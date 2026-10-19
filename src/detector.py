from pathlib import Path

import cv2

import time
import cv2

MAX_DETECTION_SIZE = 1280

MODEL_PATH = Path(__file__).resolve().parent.parent / "models"


class DetectorYuNet:
    """YuNet face detector based on a convolutional neural network."""

    name = "YuNet (deep learning)"

    def __init__(self, confidence_threshold=0.7):
        model_file = MODEL_PATH / "face_detection_yunet_2023mar.onnx"

        self.network = cv2.FaceDetectorYN.create(
            str(model_file),
            "",
            (320, 320),
            score_threshold=confidence_threshold,
            nms_threshold=0.3,
            top_k=5000,
        )

    def detect(self, image):
        height, width = image.shape[:2]
        self.network.setInputSize((width, height))

        _, faces = self.network.detect(image)

        if faces is None:
            return []

        return [
            tuple(float(value) for value in face[:4])
            for face in faces
        ]

    detectar = detect

def detect_largest_face(detector, image):
    """
    Detect the largest face in an image.

    Args:
        detector: Face detector instance.
        image: OpenCV BGR image.

    Returns:
        Tuple containing:
        - Largest face (x, y, width, height), or None.
        - Detection time in milliseconds.
    """
    height, width = image.shape[:2]

    scale = min(
        1.0,
        MAX_DETECTION_SIZE / max(height, width),
    )

    # Resize image for faster detection
    resized_image = (
        image
        if scale == 1.0
        else cv2.resize(
            image,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_AREA,
        )
    )

    start = time.perf_counter()

    faces = detector.detectar(resized_image)

    elapsed_ms = (
        time.perf_counter() - start
    ) * 1000

    if not faces:
        return None, elapsed_ms

    # Select the face with the largest bounding box
    largest_face = max(
        faces,
        key=lambda face: face[2] * face[3],
    )

    # Restore original image coordinates
    largest_face = tuple(
        value / scale
        for value in largest_face
    )

    return largest_face, elapsed_ms
