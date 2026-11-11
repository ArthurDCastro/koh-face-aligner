
from pathlib import Path

import cv2
import numpy as np
from src.validation import read_image_bytes, ValidationError


def load_image(path):
    """Load an image with Unicode path support."""
    path = Path(path)

    data, _ = read_image_bytes(path)
    try:
        image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    except cv2.error as error:
        raise ValidationError("decode_failed", "Unable to decode image.", str(error)) from error

    if image is None:
        raise ValidationError("decode_failed", "Unable to decode image.", str(path))

    return image


def save_image(path, image):
    """Save an image with Unicode path support."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    extension = path.suffix.lower()

    success, encoded = cv2.imencode(extension, image)

    if not success:
        raise IOError(f"Failed to encode image: {path}")

    encoded.tofile(str(path))
