# KOH - Keypoint-Oriented Harmonization

**Tutorial / Language:** 🇺🇸 **[English (default)](docs/tutorials/koh-tutorial-en.md)** · 🇧🇷 [Português](docs/tutorials/koh-tutorial-pt-BR.md) · 🇪🇸 [Español](docs/tutorials/koh-tutorial-es.md)

KOH is a cross-platform desktop application for automatic face detection, alignment, and image standardization, focused on portraits. The project uses computer vision to locate the largest face in an image, center it according to configurable proportions, and export the result at standardized dimensions. It also offers optional background removal using fast processing or AI-based methods.

## Overview

The main workflow is to:

- detect the main face in an image;
- center and resize the face based on parameters such as output width, height, and face ratio;
- crop and position the subject to standardize the composition;
- save the final image to an output directory;
- optionally remove the background using the project's processing methods.

The graphical interface supports batch processing of multiple files or entire folders.

## Features

- Face detection using YuNet;
- Selection of the largest detected face;
- Configurable face ratio and horizontal/vertical position;
- Batch image processing;
- Automatic input validation with valid/invalid counts, failure reasons, retry, and removal of invalid files;
- Live batch progress with percentage, completed/total images, current filename, elapsed time, and estimated remaining time;
- Live list and counter of images with errors, including the failure reason;
- Progress bar keeps the theme's default color without errors, turns amber for partial failures, and raspberry red if every image fails or batch processing stops with an error;
- Side-by-side original/result previews with navigation, zoom, fit, and checkerboard transparency;
- JPG and PNG export;
- Background removal modes: `none`, `fast`, and `ai`;
- Windows, Linux, and macOS (Intel and Apple Silicon) support.

## User tutorial

For a detailed walkthrough of the interface, image settings, processing modes, and export behavior, read the **[KOH Tutorial (English)](docs/tutorials/koh-tutorial-en.md)**.

Also available in [Português 🇧🇷](docs/tutorials/koh-tutorial-pt-BR.md) and [Español 🇪🇸](docs/tutorials/koh-tutorial-es.md).

## Project structure

- `src/main.py` — application entry point;
- `src/interface.py` — PySide6 graphical interface;
- `src/processing.py` — main processing pipeline;
- `src/detector.py` — YuNet face detector;
- `src/centralizer.py` — face centering and alignment;
- `src/segmentation.py` — MODNet background removal;
- `src/background.py` — fast background removal;
- `models/` — ONNX model weights;
- `requirements.txt` — project dependencies.

## Requirements

- Python 3.10+;
- pip;
- A virtual environment is recommended.

## Download executables

Windows, Linux (Ubuntu), and macOS executables are built using GitHub Actions.

**[Download KOH builds (GitHub Actions)](https://github.com/ArthurDCastro/koh-face-aligner/actions/workflows/build.yml)**

1. Open the link and select the most recent successful **Build KOH** workflow run.
2. Under **Artifacts**, download the package for your platform:
   - **Windows:** `KOH-v<version>-windows-x64` — extract the ZIP and run `KOH-v<version>-windows-x64.exe`.
   - **Ubuntu (Linux):** `KOH-v<version>-linux-x64` — extract the tar.gz archive and run `KOH-v<version>-linux-x64/KOH-v<version>-linux-x64`. If necessary, make that executable runnable with `chmod +x`.
   - **macOS (Intel):** `KOH-v<version>-macos-x64` — extract the ZIP and open `KOH-v<version>-macos-x64.app`.
   - **macOS (Apple Silicon / M-series):** `KOH-v<version>-macos-arm64` — extract the ZIP and open `KOH-v<version>-macos-arm64.app`.

`<version>` is the application version shown in the artifact name. GitHub may wrap the package in an additional ZIP; extract that wrapper first, then extract the contained application package.

> GitHub may require you to sign in to download workflow artifacts. Downloads appear only for runs that successfully uploaded the build artifacts.

### Which macOS download should I choose?

The two macOS packages are for **different Mac processor architectures**, not different macOS operating system versions. Choose based on the processor in your Mac:

| Your Mac | Processor / chip | Download |
| --- | --- | --- |
| Intel-based Mac (typically older models) | Intel Core i5, i7, i9, Xeon, etc. (x86-64) | `KOH-v<version>-macos-x64` |
| Apple Silicon Mac | Apple M1, M2, M3, M4, M5, or another M-series chip (ARM64) | `KOH-v<version>-macos-arm64` |

**How to check your Mac:**

1. Click the **Apple menu () → About This Mac**.
2. Look for **Chip** or **Processor**:
   - If it says **Apple M1**, **M2**, **M3**, **M4**, **M5**, etc., download **macOS Apple Silicon (ARM64)**.
   - If it says **Intel**, download **macOS Intel (x64)**.
3. Extract the downloaded ZIP and open the versioned KOH `.app` bundle.

**Important:** The Intel and Apple Silicon packages contain the same KOH application and features; they differ in the native binaries used by their processors. The ARM64 build is the recommended native version for Apple Silicon. Although some Intel applications can run on Apple Silicon through Rosetta 2, use the ARM64 package whenever available. An ARM64 app will not run natively on an Intel Mac.

These downloads do not imply support for every macOS release: the minimum compatible macOS version depends on the bundled dependencies and has not yet been established through testing.

### macOS first launch

The macOS packages are currently unsigned and not notarized. macOS Gatekeeper may warn that it cannot verify the developer. If you trust the build, open **System Settings → Privacy & Security** and select **Open Anyway** after attempting to launch the KOH `.app` bundle. Follow the on-screen confirmation. Do not disable Gatekeeper globally.

Both macOS variants use native Python dependencies and are built independently on their matching GitHub Actions runner. A successful build does not replace a functional test on a real Mac.

## Installation

Clone the repository and install the dependencies:

```bash
git clone https://github.com/ArthurDCastro/koh-face-aligner.git
cd koh-face-aligner
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

You can also use the installation script:

```bash
bash install.sh
```

## Running the application

```bash
source .venv/bin/activate
python -m src.main
```

The interface lets you select images, choose an output folder, configure output dimensions and face positioning, select the background removal mode, and start batch processing.

Click **About KOH** to see the version and build target. From source, `python -m src.main --version` or `python -m src.main -V` prints the version without loading the GUI or models. The packaged executable supports the same flags; on macOS, invoke the executable inside the app's `Contents/MacOS/` directory.

To remove specific images from the input list, select them (use Ctrl/Cmd or Shift for multiple images) and click **Remove Selected**. **Clear** removes the entire list. These actions only change the input list; files on disk are preserved.

During processing, elapsed time updates every second. Remaining time shows **Calculating...** until two images have completed, then uses the average duration of the last 10 images (including failed attempts). Estimates adjust as the current image runs and may vary with image complexity and processing mode. Successful and failed images both advance progress. Each new batch resets the counters and timer; the final duration remains visible when processing finishes or fails.

### Input validation

Images are checked automatically after **Add Images** or **Add Folder**. The input area shows **Valid**, **Invalid**, and **Checking** counts. Invalid rows show the filename and reason; hover over a row for its full path, error category, and technical details. Select files and click **Retry Validation** after fixing their access or contents. With no selection, retry checks all invalid files. **Remove Invalid** removes invalid entries from the list without deleting files.

**Process Images** includes only files already marked valid when you start the batch. Invalid files and files still being checked remain in the list for a later batch; they do not block valid images. Individual previews are also enabled only after validation succeeds. Validation checks actual read access, nonempty regular files, image headers/integrity, and an OpenCV decode using the same decoder as processing. Supported content formats are JPEG, PNG, BMP, and WebP, subject to the 40 MP input limit. **All Files** in the file picker lets you select an image with an unusual extension; validation checks its contents. Folder import discovers the usual image extensions and iCloud placeholder names.

Locally accessible files in cloud folders work normally. Recognizable Windows offline/recall flags, macOS dataless flags, iCloud stubs, and cloud-provider errors show a download/available-offline instruction. Provider behavior varies; unidentified read failures and timeouts suggest checking storage or downloading locally rather than claiming the file is corrupt. After making a cloud file available offline, retry validation (or add the downloaded image if its placeholder name changed).

Folder discovery and validation run outside the GUI thread. A reusable isolated validator reads/decodes one image at a time, returns metadata instead of retaining full images, and applies a 15-second timeout and a 1 GB memory limit per request. Failed requests do not stop the remaining checks. Duplicate paths are not queued again, and replies for removed entries or older retry attempts are ignored. Diagnostic records include filename, path, category, message, and technical details in the validation state and application log. Processing still reopens and checks each input, so files that disappear or become unreadable after validation are reported through the existing batch error list.

### Image preview and comparison

Select an image in the input list or use **Previous** / **Next** in the preview panel. The original appears on the left and the processed result on the right. **+** / **−** zoom both views; drag to pan, or click **Fit** to restore the aspect-preserving fit. Transparent regions appear over a checkerboard.

Click **Preview Image** to process only the displayed image with the current output dimensions, face ratio, position, and background removal mode. No output folder is required. This uses the same isolated worker and processing pipeline as the batch, writes to a temporary directory, then deletes the temporary output after loading its preview. It does not add failures to the batch error count; preview errors appear beside the processed view and can be retried.

During a batch, keep browsing the input list to inspect results as each image finishes. Images that failed or have no output show an explanatory message. Saved batch results remain available afterward; if you change settings, the panel identifies the saved result as using earlier settings. Click **Preview Image** to check the new settings before running another batch.

Image loading and individual processing run in the background. The GUI keeps a maximum of eight resized images (up to 1024 pixels per side), rather than all full-resolution inputs. Navigating uses existing outputs or cached previews; it does not trigger processing. Individual preview processing and batch processing run separately in time, so wait for an individual preview to finish before starting a batch or closing the app. Zoom enlarges the resized preview rather than loading the full-resolution image.

GUI progress, preview, and validation tests run without loading models:

```bash
QT_QPA_PLATFORM=offscreen python -m unittest tests.test_progress tests.test_preview tests.test_validation tests.test_version -v
```

## Versioning, builds, and releases

[`src/version.py`](src/version.py) is the single source of truth. Change only its `VERSION` constant to update the application version; the GUI, CLI, Qt metadata, Windows properties, macOS bundle metadata, and artifact names all derive from it. The package also exposes this value as `src.__version__`.

Versions use SemVer's `MAJOR.MINOR.PATCH` format, with no leading zeros or prerelease/build suffixes. KOH is currently pre-1.0: increment PATCH for compatible fixes and MINOR for features or changes to the evolving interface. Reserve a MAJOR bump for an established compatibility boundary; at and after 1.0, breaking changes increment MAJOR, compatible features MINOR, and fixes PATCH. See the [SemVer specification](https://semver.org/).

Build on the target operating system and architecture after installing the project dependencies:

```bash
python scripts/build.py --metadata
python scripts/build.py --package
```

The build script reads the portable [`scripts/koh.spec`](scripts/koh.spec), verifies the generated executable's `--version` output, and packages it under `dist/`. Windows produces a versioned `.exe` and `.zip`, Linux a versioned directory and `.tar.gz`, and macOS a versioned `.app` and `.zip`. A bundled `build-info.json` identifies the version and target. Windows Product Name stays KOH; Product/File Version strings use the SemVer value and numeric version fields append a zero as the fourth component. macOS keeps the stable `com.arthurdcastro.koh` bundle identifier and KOH display name, with both native version fields set before signing. Windows double-click launches hide the console while command-line launches retain version output.

After updating `VERSION`, running tests, and committing the release changes, create a matching annotated tag from that commit:

```bash
tag="$(python -c 'from src.version import VERSION; print("v" + VERSION)')"
git tag -a "$tag" -m "KOH $tag"
git push origin HEAD
git push origin "$tag"
```

The existing **Build KOH** workflow runs for `v*` tags and manual dispatch. It rejects any tag that differs from `v` plus the source version, verifies the native target against the job matrix, checks executable versions, and uploads artifacts named with version, platform, and architecture. Manual branch builds use the source version. There is no separate workflow version to update.

To publish a release, wait for all four platform builds for the tag to succeed. Download and extract the Actions artifact wrappers, then create a GitHub Release using that exact existing tag. Add release notes and attach the generated Windows/macOS ZIPs and Linux tar.gz archive. Review the assets before publishing. The build workflow does not publish releases automatically. For fixes after publication, bump the version and create a new tag rather than moving an existing release tag.

## Models and credits

This project uses third-party AI models for face detection and background removal. The original research and implementations are credited below.

### 1) YuNet — face detection

YuNet is used to detect faces efficiently in images.

- Paper: Wu, W., Peng, H., Yu, S. "YuNet: A tiny millisecond-level face detector". *Machine Intelligence Research*, 2023.

```bibtex
@article{wu2023yunet,
  title={Yunet: A tiny millisecond-level face detector},
  author={Wu, Wei and Peng, Hanyang and Yu, Shiqi},
  journal={Machine Intelligence Research},
  volume={20},
  number={5},
  pages={656--665},
  year={2023},
  publisher={Springer}
}
```

The model file is `models/face_detection_yunet_2023mar.onnx`.

### 2) MODNet — portrait matting and background removal

MODNet is a trimap-free portrait matting model used to estimate alpha masks and remove backgrounds.

- Paper: Ke, Z., Sun, J., Li, K., Yan, Q., Lau, R. W. H. "MODNet: Real-Time Trimap-Free Portrait Matting via Objective Decomposition". *AAAI*, 2022.

```bibtex
@InProceedings{MODNet,
  author = {Zhanghan Ke and Jiayu Sun and Kaican Li and Qiong Yan and Rynson W.H. Lau},
  title = {MODNet: Real-Time Trimap-Free Portrait Matting via Objective Decomposition},
  booktitle = {AAAI},
  year = {2022},
}
```

The model file is `models/modnet/modnet_photographic.onnx`.

### Attribution and redistribution

The models above are credited to their original authors. Academic references do not replace the models' licenses or other third-party notices. Check the applicable terms before redistributing the model weights and bundled dependencies.

## Main technologies

- Python
- OpenCV / OpenCV Contrib
- PySide6
- NumPy
- ONNX Runtime
- PyInstaller

## License

The original KOH source code is distributed under the [MIT License](LICENSE), allowing use, modification, and redistribution, including commercial use, while retaining the required copyright and license notices.

YuNet, MODNet, and bundled third-party libraries remain subject to their own licenses. Review their redistribution requirements when packaging the application.

## Notes

- KOH is designed to standardize portraits and process images in batches.
- The `ai` mode uses MODNet, although older or more generic labels may still appear in parts of the interface.
- For best results, use images with clearly visible faces and good lighting.
