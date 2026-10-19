
from pathlib import Path

import cv2
import psutil


class ResourceManager:
    """Validate image sizes and monitor process memory."""

    def __init__(
        self,
        max_memory_mb=2048,
        max_megapixels=20,
        max_output_dimension=4096,
    ):
        self.max_memory_mb = max_memory_mb
        self.max_megapixels = max_megapixels
        self.max_output_dimension = max_output_dimension

    def validate_image(self, image_path):
        """Check image dimensions before decoding."""
        image_path = Path(image_path)

        if not image_path.is_file():
            raise FileNotFoundError(
                f"Image not found: {image_path}"
            )

        # Read metadata to avoid loading large pixel arrays
        from PIL import Image, UnidentifiedImageError

        try:
            with Image.open(image_path) as image:
                width, height = image.size
        except (OSError, UnidentifiedImageError) as error:
            raise ValueError(
                f"Invalid image: {image_path}"
            ) from error

        megapixels = width * height / 1_000_000

        if megapixels > self.max_megapixels:
            raise ValueError(
                f"Image exceeds {self.max_megapixels} MP "
                f"({megapixels:.2f} MP)."
            )

    def validate_output(self, width, height):
        """Validate requested output resolution."""
        if not (
            0 < width <= self.max_output_dimension
            and 0 < height <= self.max_output_dimension
        ):
            raise ValueError(
                "Output dimensions exceed allowed limits."
            )

    def get_memory_mb(self, pid=None):
        """Return resident memory usage in MB."""
        process = (
            psutil.Process(pid)
            if pid is not None
            else psutil.Process()
        )

        return process.memory_info().rss / (1024 ** 2)

    def is_memory_exceeded(self, pid=None):
        """Check whether process memory exceeds the limit."""
        return self.get_memory_mb(pid) > self.max_memory_mb
