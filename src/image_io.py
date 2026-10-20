
from pathlib import Path

import cv2
import numpy as np


def load_image(path):
    """Load an image with Unicode path support."""
    path = Path(path)

    data = np.fromfile(str(path), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)

    if image is None:
        raise ValueError(f"Unable to decode image: {path}")

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
