
from pathlib import Path

import cv2

from src.detector import DetectorYuNet
from src.centralizer import Centralizer


class ImageProcessor:
    def __init__(self):
        self.detector = DetectorYuNet()
        self.centralizer = Centralizer()

    def process(
        self,
        files,
        output_dir,
        width,
        height,
        face_ratio,
        position_x=0.5,
        position_y=0.5,
        callback=None,
    ):
        """
        Process a batch of images.

        Args:
            files: List of image paths.
            output_dir: Directory where results will be saved.
            width: Output image width in pixels.
            height: Output image height in pixels.
            face_ratio: Desired face width relative to output width.
            position_x: Relative horizontal face position.
            position_y: Relative vertical face position.
            callback: Optional progress callback.

        Returns:
            Dictionary containing processing results.
        """

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results = {
            "total": len(files),
            "success": 0,
            "errors": [],
        }

        for index, file in enumerate(files, start=1):
            file = Path(file)

            try:
                image = cv2.imread(str(file))

                if image is None:
                    raise ValueError("Unable to load image.")

                faces = self.detector.detectar(image)

                if not faces:
                    raise ValueError("No faces detected.")

                # Select the largest detected face
                face = max(faces, key=lambda f: f[2] * f[3])

                # Apply face alignment and cropping
                result = self.centralizer.center(
                    image=image,
                    face=face,
                    width=width,
                    height=height,
                    face_ratio=face_ratio,
                    position_x=position_x,
                    position_y=position_y,
                )

                # Generate output filename
                output_path = output_dir / f"koh_{file.stem}.jpg"

                if not cv2.imwrite(str(output_path), result):
                    raise IOError("Failed to save image.")

                results["success"] += 1

            except Exception as error:
                results["errors"].append({
                    "file": str(file),
                    "error": str(error),
                })

            if callback:
                callback(index, len(files))

        return results
