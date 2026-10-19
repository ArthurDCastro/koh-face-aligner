
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort
from src.paths import get_resource_path



PROJECT_ROOT = Path(__file__).resolve().parent.parent

MODEL_PATH = get_resource_path(
    "models",
    "modnet",
    "modnet_photographic.onnx",
)


class AIBackgroundRemover:
    """Remove portrait backgrounds using MODNet."""

    def __init__(self, model_path=MODEL_PATH):
        model_path = Path(model_path)

        if not model_path.is_file():
            raise FileNotFoundError(
                f"MODNet model not found: {model_path}"
            )

        # Configure ONNX Runtime for CPU inference
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        options.enable_mem_pattern = False

        self.session = ort.InferenceSession(
            str(model_path),
            sess_options=options,
            providers=["CPUExecutionProvider"],
        )

        input_info = self.session.get_inputs()[0]
        self.input_name = input_info.name

        # MODNet Photographic uses a 512x512 input
        self.input_size = (512, 512)

    def create_mask(self, image):
        """
        Generate an alpha mask using MODNet.

        Args:
            image: OpenCV BGR image.

        Returns:
            Alpha mask (uint8, 0-255).
        """
        if image is None or image.size == 0:
            raise ValueError("Invalid input image.")

        height, width = image.shape[:2]

        # Resize image to model input dimensions
        resized = cv2.resize(
            image,
            self.input_size,
            interpolation=cv2.INTER_AREA,
        )

        # Convert BGR to RGB
        rgb = cv2.cvtColor(
            resized,
            cv2.COLOR_BGR2RGB,
        )

        # Normalize to [-1, 1]
        normalized = (
            rgb.astype(np.float32) / 127.5
        ) - 1.0

        # Convert HWC to NCHW
        tensor = np.transpose(
            normalized,
            (2, 0, 1),
        )[np.newaxis, ...]

        tensor = np.ascontiguousarray(tensor)

        # Run inference
        outputs = self.session.run(
            None,
            {self.input_name: tensor},
        )

        # MODNet returns an alpha matte
        matte = np.squeeze(outputs[0])

        # Restore original image dimensions
        matte = cv2.resize(
            matte,
            (width, height),
            interpolation=cv2.INTER_LINEAR,
        )

        # Convert alpha values to uint8
        alpha = np.clip(
            matte * 255,
            0,
            255,
        ).astype(np.uint8)

        return alpha

    def remove_background(self, image):
        """
        Remove background and return a BGRA image.
        """
        alpha = self.create_mask(image)

        result = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2BGRA,
        )

        result[:, :, 3] = alpha

        return result
