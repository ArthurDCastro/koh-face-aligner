
import cv2
import psutil
from src.validation import MAX_MEGAPIXELS, inspect_image


class ResourceManager:
    """Validate image sizes and monitor process memory."""

    def __init__(
        self,
        max_memory_mb=2048,
        max_megapixels=MAX_MEGAPIXELS,
        max_output_dimension=4096,
    ):
        self.max_memory_mb = max_memory_mb
        self.max_megapixels = max_megapixels
        self.max_output_dimension = max_output_dimension

    def validate_image(self, image_path):
        """Check image dimensions before decoding."""
        return inspect_image(image_path, self.max_megapixels)

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
