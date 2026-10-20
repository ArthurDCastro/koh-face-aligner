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
- JPG and PNG export;
- Background removal modes: `none`, `fast`, and `ai`;
- Windows and Linux support.

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

Windows and Linux (Ubuntu) executables are built using GitHub Actions.

**[Download KOH builds (GitHub Actions)](https://github.com/ArthurDCastro/koh-face-aligner/actions/workflows/build.yml)**

1. Open the link and select the most recent successful **Build KOH** workflow run.
2. Under **Artifacts**, download the package for your platform:
   - **Windows:** `KOH-windows-x64` — extract the ZIP and run `KOH.exe`.
   - **Ubuntu (Linux):** `KOH-linux-x64` — extract the archive and run `KOH/KOH`. If necessary, run `chmod +x KOH/KOH`.

> GitHub may require you to sign in to download workflow artifacts. Downloads appear only for runs that successfully uploaded the build artifacts.

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
