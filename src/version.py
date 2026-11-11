"""Application identity and the single editable SemVer version."""
import platform
import re
import sys

APP_NAME = "KOH"
APP_DESCRIPTION = "Keypoint-Oriented Harmonization"
BUNDLE_IDENTIFIER = "com.arthurdcastro.koh"
VERSION = "0.2.1"


def version_parts(version=VERSION):
    if not re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", version):
        raise ValueError(f"Invalid version {version!r}: expected MAJOR.MINOR.PATCH without leading zeros")
    return tuple(int(part) for part in version.split("."))


VERSION_PARTS = version_parts()


def check_tag(tag):
    if tag and tag != f"v{VERSION}":
        raise ValueError(f"Git tag {tag!r} does not match application version v{VERSION}")


def build_identity(system=None, machine=None):
    system = sys.platform if system is None else system
    machine = platform.machine() if machine is None else machine
    systems = {"win32": "windows", "linux": "linux", "darwin": "macos"}
    architectures = {"x86_64": "x64", "amd64": "x64", "x64": "x64",
                     "aarch64": "arm64", "arm64": "arm64"}
    try:
        target = systems[system]
        architecture = architectures[machine.lower()]
    except KeyError as error:
        raise ValueError(f"Unsupported build target: {system}/{machine}") from error
    artifact = f"{APP_NAME}-v{VERSION}-{target}-{architecture}"
    extension = ".tar.gz" if target == "linux" else ".zip"
    return {"name": APP_NAME, "version": VERSION, "platform": target,
            "architecture": architecture, "artifact": artifact,
            "archive": f"dist/{artifact}{extension}"}
