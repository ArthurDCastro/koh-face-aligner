import cv2
import numpy as np


class Centralizer:
    """Standardizes the scale and position of faces in images."""

    def center(
        self,
        image,
        face,
        width,
        height,
        face_ratio,
        position_x=0.5,
        position_y=0.5,
        background_color=(255, 255, 255),
    ):
        """
        Args:
            image: original image (numpy.ndarray).
            face: detected face coordinates (x, y, w, h).
            width: final image width in pixels.
            height: final image height in pixels.
            face_ratio: fraction of the final width occupied by the face.
            position_x: relative horizontal position of the face center.
            position_y: relative vertical position of the face center.
            background_color: border fill color (BGR).

        Returns:
            Centered image (numpy.ndarray).
        """

        if image is None or image.size == 0:
            raise ValueError("Invalid image.")

        if width <= 0 or height <= 0:
            raise ValueError("Invalid dimensions.")

        if not 0 < face_ratio <= 1:
            raise ValueError("Face ratio must be between 0 and 1.")

        if not 0 <= position_x <= 1 or not 0 <= position_y <= 1:
            raise ValueError("Positions must be between 0 and 1.")

        x, y, w, h = map(float, face[:4])

        if w <= 0 or h <= 0:
            raise ValueError("Invalid face dimensions.")

        # Center of the original face
        face_center_x = x + w / 2
        face_center_y = y + h / 2

        # Scale to achieve the desired face ratio
        scale = (width * face_ratio) / w

        # Desired center in the final image
        target_x = width * position_x
        target_y = height * position_y

        # Required translation
        translation_x = target_x - scale * face_center_x
        translation_y = target_y - scale * face_center_y

        transform = np.array([
            [scale, 0, translation_x],
            [0, scale, translation_y]
        ], dtype=np.float64)

        return cv2.warpAffine(
            image,
            transform,
            (width, height),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=background_color,
        )

    centralizar = center


Centralizador = Centralizer
