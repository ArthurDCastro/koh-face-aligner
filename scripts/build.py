"""Build, verify and optionally package the versioned native KOH application."""
import argparse
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tarfile
import zipfile

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.version import APP_NAME, BUNDLE_IDENTIFIER, VERSION, VERSION_PARTS, build_identity, check_tag

MODELS_DIR = PROJECT_ROOT / "models"


def windows_version_resource(executable):
    if any(part > 65535 for part in VERSION_PARTS):
        raise ValueError("Windows version components must fit in 16 bits")
    numeric = VERSION_PARTS + (0,)
    strings = {
        "CompanyName": "Arthur Castro", "FileDescription": APP_NAME,
        "FileVersion": VERSION, "InternalName": APP_NAME,
        "OriginalFilename": executable, "ProductName": APP_NAME,
        "ProductVersion": VERSION,
    }
    entries = ",\n".join(f"StringStruct({key!r}, {value!r})" for key, value in strings.items())
    return (
        "VSVersionInfo(\n"
        f"ffi=FixedFileInfo(filevers={numeric!r}, prodvers={numeric!r}, "
        "mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),\n"
        f"kids=[StringFileInfo([StringTable('040904B0', [{entries}])]),\n"
        "VarFileInfo([VarStruct('Translation', [1033, 1200])])])\n"
    )


def macos_info_plist():
    return {"CFBundleName": APP_NAME, "CFBundleDisplayName": APP_NAME,
            "CFBundleIdentifier": BUNDLE_IDENTIFIER,
            "CFBundleShortVersionString": VERSION, "CFBundleVersion": VERSION}


def executable_path(identity, dist_dir):
    artifact = identity["artifact"]
    if identity["platform"] == "windows":
        return dist_dir / f"{artifact}.exe"
    if identity["platform"] == "macos":
        return dist_dir / f"{artifact}.app" / "Contents" / "MacOS" / artifact
    return dist_dir / artifact / artifact


def prepare_metadata(identity):
    build_dir = PROJECT_ROOT / "build"
    build_dir.mkdir(parents=True, exist_ok=True)
    (build_dir / "build-info.json").write_text(json.dumps(identity, indent=2) + "\n", encoding="utf-8")
    if identity["platform"] == "windows":
        (build_dir / "windows-version.txt").write_text(
            windows_version_resource(f"{identity['artifact']}.exe"), encoding="utf-8"
        )


def verify_build(identity, dist_dir):
    executable = executable_path(identity, dist_dir)
    if not executable.is_file():
        raise FileNotFoundError(f"Built executable not found: {executable}")
    result = subprocess.run([str(executable), "--version"], check=True, capture_output=True, text=True, timeout=60)
    if result.stdout.strip() != f"{APP_NAME} {VERSION}":
        raise RuntimeError(f"Built application reports an unexpected version: {result.stdout!r}")
    if identity["platform"] == "macos":
        info_path = executable.parent.parent / "Info.plist"
        with info_path.open("rb") as stream:
            info = plistlib.load(stream)
        for key, value in macos_info_plist().items():
            if info.get(key) != value:
                raise RuntimeError(f"macOS metadata {key} does not match {value!r}")


def package_build(identity, dist_dir):
    artifact = identity["artifact"]
    archive = dist_dir / Path(identity["archive"]).name
    if identity["platform"] == "linux":
        with tarfile.open(archive, "w:gz") as package:
            package.add(dist_dir / artifact, arcname=artifact)
    elif identity["platform"] == "windows":
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as package:
            executable = executable_path(identity, dist_dir)
            package.write(executable, arcname=executable.name)
    else:
        subprocess.run(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent",
                        str(dist_dir / f"{artifact}.app"), str(archive)], check=True)
    return archive


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", action="store_true", help="Print build identity without building")
    parser.add_argument("--github-output", type=Path, help="Append metadata to a GitHub Actions output file")
    parser.add_argument("--package", action="store_true", help="Package the verified build")
    parser.add_argument("--expected-platform", choices=["linux", "windows", "macos"])
    parser.add_argument("--expected-architecture", choices=["x64", "arm64"])
    parser.add_argument("--tag", default=os.environ.get("GITHUB_REF_NAME", "") if os.environ.get("GITHUB_REF_TYPE") == "tag" else "")
    args = parser.parse_args(argv)
    try:
        check_tag(args.tag)
        identity = build_identity()
        for key, expected in (("platform", args.expected_platform), ("architecture", args.expected_architecture)):
            if expected and identity[key] != expected:
                raise ValueError(f"Expected {key} {expected!r}, running on {identity[key]!r}")
    except ValueError as error:
        parser.error(str(error))
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as output:
            for key, value in identity.items():
                output.write(f"{key}={value}\n")
    if args.metadata:
        print(json.dumps(identity, indent=2))
        return 0

    for model in (MODELS_DIR / "face_detection_yunet_2023mar.onnx", MODELS_DIR / "modnet" / "modnet_photographic.onnx"):
        if not model.is_file():
            raise FileNotFoundError(f"Required model not found: {model}")
    prepare_metadata(identity)
    import PyInstaller.__main__
    PyInstaller.__main__.run([
        str(PROJECT_ROOT / "scripts" / "koh.spec"), "--noconfirm", "--clean",
        "--distpath", str(PROJECT_ROOT / "dist"), "--workpath", str(PROJECT_ROOT / "build"),
    ])
    verify_build(identity, PROJECT_ROOT / "dist")
    if args.package:
        print(f"Created {package_build(identity, PROJECT_ROOT / 'dist')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
