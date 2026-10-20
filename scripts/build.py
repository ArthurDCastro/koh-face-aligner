import os
import sys
from pathlib import Path

import PyInstaller.__main__


PROJECT_ROOT = Path(__file__).resolve().parent.parent

APP_NAME = "KOH"
ENTRY_POINT = PROJECT_ROOT / "src" / "main.py"
MODELS_DIR = PROJECT_ROOT / "models"

ICON_DIR = PROJECT_ROOT / "assets" / "icons"


def main():
    if not MODELS_DIR.is_dir():
        raise FileNotFoundError(
            f"Models directory not found: {MODELS_DIR}"
        )

    required_models = [
        MODELS_DIR / "face_detection_yunet_2023mar.onnx",
        MODELS_DIR / "modnet" / "modnet_photographic.onnx",
    ]

    for model in required_models:
        if not model.is_file():
            raise FileNotFoundError(
                f"Required model not found: {model}"
            )

    arguments = [
        str(ENTRY_POINT),
        "--name", APP_NAME,
        "--onefile" if sys.platform == "win32" else "--onedir",
        "--windowed",
        "--clean",
        "--hidden-import=src.worker",
        "--noconfirm",
        "--paths", str(PROJECT_ROOT),
        "--distpath", str(PROJECT_ROOT / "dist"),
        "--workpath", str(PROJECT_ROOT / "build"),
        "--specpath", str(PROJECT_ROOT),
        "--add-data",
        f"{MODELS_DIR}{os.pathsep}models",
        "--add-data",
        f"{ICON_DIR}{os.pathsep}assets/icons",
    ]

    if sys.platform == "linux":
        print("Building KOH for Linux...")
    elif sys.platform == "win32":
        print("Building KOH for Windows...")
    else:
        raise RuntimeError("Unsupported operating system.")

    if sys.platform == "win32":
        arguments.extend([
            "--icon",
            str(ICON_DIR / "koh.ico"),
        ])
    elif sys.platform == "linux":
        arguments.extend([
            "--icon",
            str(ICON_DIR / "koh.png"),
        ])

    # Run PyInstaller on both platforms
    PyInstaller.__main__.run(arguments)


if __name__ == "__main__":
    main()
