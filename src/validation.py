"""Content-based input validation, also used by the isolated validator process."""
from contextlib import contextmanager
import errno
import argparse
from io import BytesIO
import json
import logging
import os
from pathlib import Path
import stat
import sys
import time


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
SUPPORTED_FORMATS = {"JPEG", "PNG", "BMP", "WEBP"}
MAX_MEGAPIXELS = 40
LOGGER = logging.getLogger(__name__)
OFFLINE_MESSAGE = "File is not available locally. Download it or make it available offline, then retry validation."


class ValidationError(ValueError):
    def __init__(self, category, message, details=""):
        super().__init__(message)
        self.category = category
        self.details = details or message


def error_record(file, error):
    """Keep the existing file/error fields while adding diagnostic context."""
    category = "unexpected_error"
    message = "Unexpected error while reading the image."
    details = f"{type(error).__name__}: {error}"
    if isinstance(error, ValidationError):
        category, message, details = error.category, str(error), error.details
    elif isinstance(error, OSError) and getattr(error, "winerror", None) in {362, 389, 4350}:
        # Cloud provider not running, cloud operation unsuccessful, file offline.
        category, message = "cloud_unavailable", OFFLINE_MESSAGE
    elif isinstance(error, FileNotFoundError):
        category, message = "missing_file", "File not found. Check its location and retry."
    elif isinstance(error, PermissionError):
        category, message = "permission_denied", "Permission denied. Grant read access and retry."
    elif isinstance(error, OSError):
        category, message = "unreadable_file", "Unable to read file. Check the drive or cloud sync status and retry."
        if error.errno in {getattr(errno, "ENODATA", -1), getattr(errno, "ENETDOWN", -2),
                           getattr(errno, "ENETUNREACH", -3), getattr(errno, "ENOTCONN", -4)}:
            category, message = "unavailable_file", "File storage is unavailable. Reconnect or make the file available offline, then retry."
        # Providers may expose a specific cloud error through their OS message.
        if "cloud" in str(error).lower() or "offline" in str(error).lower():
            category, message = "cloud_unavailable", OFFLINE_MESSAGE
    return {"file": str(file), "path": str(file), "filename": Path(file).name,
            "valid": False, "category": category, "error": message, "details": details}


def check_metadata(file, metadata):
    if not stat.S_ISREG(metadata.st_mode):
        raise ValidationError("not_regular_file", "Path does not point to a regular file.")
    attributes = getattr(metadata, "st_file_attributes", 0)
    # Windows FILE_ATTRIBUTE_OFFLINE / RECALL_ON_OPEN / RECALL_ON_DATA_ACCESS.
    offline = attributes & (0x1000 | 0x40000 | 0x400000)
    # macOS SF_DATALESS; a reparse point or sparse file alone is not a placeholder.
    dataless = getattr(metadata, "st_flags", 0) & getattr(stat, "SF_DATALESS", 0x40000000)
    icloud_stub = Path(file).name.startswith(".") and Path(file).suffix.lower() == ".icloud"
    if offline or dataless or icloud_stub:
        raise ValidationError("cloud_unavailable", OFFLINE_MESSAGE,
                              f"attributes={attributes:#x}, flags={getattr(metadata, 'st_flags', 0):#x}, iCloud stub={icloud_stub}")
    if metadata.st_size == 0:
        raise ValidationError("empty_file", "File is empty. Restore or download the original and retry.")


@contextmanager
def open_readable(file):
    """Check real OS access, not permission bits or os.access(), and reject special files."""
    file = Path(file)
    check_metadata(file, file.stat())
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(str(file), flags), "rb") as stream:
        check_metadata(file, os.fstat(stream.fileno()))
        yield stream


def read_image_bytes(file):
    with open_readable(file) as stream:
        before = os.fstat(stream.fileno())
        data = stream.read()
        after = os.fstat(stream.fileno())
    if not data:
        raise ValidationError("empty_file", "File is empty or its contents are unavailable.")
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or len(data) != after.st_size:
        raise ValidationError("changed_file", "File changed while being read. Wait for syncing to finish and retry.")
    return data, after


def validate_image(file):
    """Verify headers/integrity and perform exactly one full OpenCV decode per attempt."""
    from PIL import Image, UnidentifiedImageError
    import cv2
    import numpy as np

    try:
        data, metadata = read_image_bytes(file)
        try:
            with Image.open(BytesIO(data)) as image:
                format_name = image.format
                width, height = image.size
                if format_name not in SUPPORTED_FORMATS:
                    raise ValidationError("unsupported_format", f"Unsupported image format: {format_name}.")
                if width * height > MAX_MEGAPIXELS * 1_000_000:
                    raise ValidationError("too_large", f"Image exceeds the existing {MAX_MEGAPIXELS} MP input limit.")
                image.verify()
                if format_name == "JPEG" and data.rfind(b"\xff\xd9") < data.rfind(b"\xff\xda"):
                    raise ValidationError("invalid_image", "JPEG image is truncated. Restore or download the complete file.", "JPEG end-of-image marker missing after the final scan")
        except UnidentifiedImageError as error:
            raise ValidationError("invalid_image", "File is not a recognized image or its header is corrupted.", str(error)) from error
        except (OSError, SyntaxError, ValueError) as error:
            if isinstance(error, ValidationError):
                raise
            raise ValidationError("invalid_image", "Image is corrupted or has invalid image data.", str(error)) from error
        try:
            decoded = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
        except cv2.error as error:
            raise ValidationError("decode_failed", "Image data could not be decoded by the processing pipeline.", str(error)) from error
        if decoded is None:
            raise ValidationError("decode_failed", "Image data could not be decoded by the processing pipeline.")
        return {"file": str(file), "path": str(file), "filename": Path(file).name,
                "valid": True, "category": None, "error": None, "details": "",
                "format": format_name, "width": width, "height": height,
                "signature": [metadata.st_size, metadata.st_mtime_ns]}
    except Exception as error:
        result = error_record(file, error)
        LOGGER.warning("Image validation failed: %s", json.dumps(result, ensure_ascii=False))
        return result


def list_images(folder):
    """Discover candidates without stat/open calls in the GUI thread."""
    return [str(file) for file in sorted(Path(folder).iterdir())
            if file.suffix.lower() in SUPPORTED_EXTENSIONS
            or (file.name.startswith(".") and file.name.lower().endswith(".icloud")
                and Path(file.stem).suffix.lower() in SUPPORTED_EXTENSIONS)]


def serve(directory):
    """One reusable decoder process; atomic JSON reports keep IPC portable on Windows."""
    request_path = Path(directory) / "request.json"
    while True:
        if not request_path.is_file():
            time.sleep(0.025)
            continue
        request = json.loads(request_path.read_text(encoding="utf-8"))
        request_path.unlink()
        file = request["file"]
        try:
            result = {"files": list_images(file)} if request.get("action") == "folder" else validate_image(file)
        except Exception as error:
            result = error_record(file, error)
        report = Path(request["report"])
        temporary = report.with_suffix(".tmp")
        temporary.write_text(json.dumps(result), encoding="utf-8")
        temporary.replace(report)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", required=True)
    args = parser.parse_args()
    return serve(args.requests)


if __name__ == "__main__":
    sys.exit(main())
