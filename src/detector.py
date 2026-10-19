from pathlib import Path

import cv2

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
