from pathlib import Path
import cv2

PASTA_MODELOS = Path(__file__).resolve().parent.parent / "models"


class DetectorYuNet:
    """Detector facial YuNet baseado em rede convolucional."""

    nome = "YuNet (deep learning)"

    def __init__(self, limiar_confianca=0.7):
        modelo = PASTA_MODELOS / "face_detection_yunet_2023mar.onnx"

        self.rede = cv2.FaceDetectorYN.create(
            str(modelo),
            "",
            (320, 320),
            score_threshold=limiar_confianca,
            nms_threshold=0.3,
            top_k=5000,
        )

    def detectar(self, imagem):
        altura, largura = imagem.shape[:2]
        self.rede.setInputSize((largura, altura))

        _, faces = self.rede.detect(imagem)

        if faces is None:
            return []

        return [
            tuple(float(v) for v in face[:4])
            for face in faces
        ]
