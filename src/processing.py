from pathlib import Path

import cv2

from src.detector import DetectorYuNet, detect_largest_face
from src.centralizer import Centralizer
from src.background import WhiteBackgroundRemover
from src.segmentation import AIBackgroundRemover
from src.resource_manager import ResourceManager
from src.image_io import load_image, save_image


class ImageProcessor:
    def __init__(self):
        self.detector = DetectorYuNet()
        self.centralizer = Centralizer()
        self.resources = ResourceManager(
            max_memory_mb=2048,
            max_megapixels=20,
        )

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
        background_mode="none",
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


        if background_mode == "fast":
            remover = WhiteBackgroundRemover(
                face_ratio=face_ratio,
                position_x=position_x,
                position_y=position_y,
            )
        elif background_mode == "ai":
            remover = AIBackgroundRemover()
        elif background_mode == "none":
            remover = None
        else:
            raise ValueError(
                f"Unsupported background mode: {background_mode}"
            )

        self.resources.validate_output(width, height)

        for index, file in enumerate(files, start=1):
            file = Path(file)

            try:
                # Validate image before loading
                self.resources.validate_image(file)

                # Load image with Unicode path support
                image = load_image(file)

                if image is None:
                    raise ValueError("Unable to load image.")

                # Detect largest face
                face, detection_time = detect_largest_face(
                    self.detector,
                    image,
                )

                if face is None:
                    raise ValueError("No faces detected.")
 
                # Center and resize the image
                result = self.centralizer.center(
                    image=image,
                    face=face,
                    width=width,
                    height=height,
                    face_ratio=face_ratio,
                    position_x=position_x,
                    position_y=position_y,
                )

                # Apply optional background removal
                if remover is not None:
                    result = remover.remove_background(result)
                    extension = ".png"
                else:
                    extension = ".jpg"

                # Save only the final image
                output_path = output_dir / f"koh_{file.stem}{extension}"

                # Encode image before writing to disk
                save_image(output_path, result)

                results["success"] += 1


            except Exception as error:
                results["errors"].append({
                    "file": str(file),
                    "error": str(error),
                })

            if callback:
                callback(index, len(files))

        return results
