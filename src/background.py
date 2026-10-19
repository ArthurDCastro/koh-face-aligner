
import cv2
import numpy as np

# Central configuration values for the background removal heuristics.
# Each key stores a numeric control used by the GrabCut mask generation.
CONTROL_VALUES = {
    # Initial face and positioning defaults.
    "face_ratio": 0.40,  # Estimated face width as a fraction of the image width.
    "position_x": 0.50,  # Horizontal center point of the face.
    "position_y": 0.40,  # Vertical center point of the face.

    # GrabCut refinement settings.
    "iterations": 10,  # Number of GrabCut refinement iterations.
    "erosion_size": 1,  # Kernel size used for edge erosion cleanup.
    "blur_size": 9,  # Gaussian blur kernel size for edge smoothing.

    # White-background detection thresholds.
    "white_value_threshold": 228,  # Brightness threshold for near-white pixels.
    "white_saturation_threshold": 27,  # Saturation threshold to ignore colorful pixels.

    # Estimated facial and torso ellipse sizing.
    "head_width_factor": 0.65,  # Head ellipse width relative to face width.
    "head_height_factor": 0.85,  # Head ellipse height relative to face width.
    "torso_top_offset_factor": 0.50, # Additional vertical offset before torso ellipse start.
    "torso_vertical_offset_ratio": 0.30,  # Lower torso vertical shift relative to image height.
    "torso_width_factor": 2.0, # Torso ellipse width relative to face width.
    "torso_height_factor": 0.65, # Torso ellipse height relative to image height.
    "inner_face_width_factor": 0.25,  # Inner face seed ellipse width.
    "inner_face_height_factor": 0.35,  # Inner face seed ellipse height.
    "torso_seed_offset_factor": 1.2,  # Torso seed vertical offset relative to face width.
    "torso_seed_width_factor": 0.50, # Torso seed ellipse width.
    "torso_seed_height_factor": 0.45,  # Torso seed ellipse height.    

    # Border cleanup and component filtering.
    "border_ratio": 0.01,  # Border width as a fraction of the shorter image dimension.
    "minimum_border_size": 4,  # Minimum border width in pixels.
    "connected_components_connectivity": 8,  # Connectivity used for foreground component analysis.
    "ellipse_angle_start": 0,  # Start angle for ellipse drawing.
    "ellipse_angle_end": 360,  # End angle for ellipse drawing.
    "grabcut_model_size": 65,  # Model vector size for GrabCut background/foreground histograms.
    "alpha_foreground": 255,  # Foreground alpha value for mask output.
    "alpha_background": 0,  # Background alpha value for mask output.
    "largest_component_offset": 1,  # Offset used to select the largest connected foreground region.
}


class WhiteBackgroundRemover:
    """Remove light backgrounds using face-guided GrabCut."""

    def __init__(
        self,
        face_ratio=CONTROL_VALUES["face_ratio"],
        position_x=CONTROL_VALUES["position_x"],
        position_y=CONTROL_VALUES["position_y"],
        iterations=CONTROL_VALUES["iterations"],
        erosion_size=CONTROL_VALUES["erosion_size"],
        blur_size=CONTROL_VALUES["blur_size"],
    ):
        self.face_ratio = face_ratio
        self.position_x = position_x
        self.position_y = position_y
        self.iterations = iterations
        self.erosion_size = erosion_size
        self.blur_size = blur_size

    def create_mask(self, image):
        """
        Create an alpha mask using GrabCut and
        estimated head and torso positions.
        """
        if image is None or image.size == 0:
            raise ValueError("Invalid input image.")

        height, width = image.shape[:2]

        # Estimated face geometry after centralization.
        # face_width is used to size the head and torso ellipses around the detected face center.
        face_width = width * self.face_ratio
        center_x = int(width * self.position_x)  # Horizontal face center in pixels.
        center_y = int(height * self.position_y)  # Vertical face center in pixels.

        # Initialize all pixels as probable background before GrabCut refinement.
        mask = np.full(
            (height, width),
            cv2.GC_PR_BGD,
            dtype=np.uint8,
        )

        # Identify near-white background pixels using HSV brightness and low saturation.
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        _, saturation, value = cv2.split(hsv)

        white_pixels = (value >= CONTROL_VALUES["white_value_threshold"]) & (
            saturation <= CONTROL_VALUES["white_saturation_threshold"]
        )
        mask[white_pixels] = cv2.GC_PR_BGD  # White background pixels are treated as probable background.

        # Non-white pixels are possible foreground, which helps GrabCut discover the subject.
        mask[~white_pixels] = cv2.GC_PR_FGD

        # Create an estimated head region centered on the face anchor.
        head_center = (center_x, center_y)
        head_axes = (
            max(1, int(face_width * CONTROL_VALUES["head_width_factor"])),
            max(1, int(face_width * CONTROL_VALUES["head_height_factor"])),
        )

        cv2.ellipse(
            mask,
            head_center,
            head_axes,
            CONTROL_VALUES["ellipse_angle_start"],
            CONTROL_VALUES["ellipse_angle_start"],
            CONTROL_VALUES["ellipse_angle_end"],
            cv2.GC_PR_FGD,
            -1,
        )

        # Create an estimated torso region below the face to guide the subject mask.
        torso_top = int(center_y + face_width * CONTROL_VALUES["torso_top_offset_factor"])
        torso_center = (
            center_x,
            int(torso_top + height * CONTROL_VALUES["torso_vertical_offset_ratio"]),
        )

        torso_axes = (
            max(1, int(face_width * CONTROL_VALUES["torso_width_factor"])),
            max(1, int(height * CONTROL_VALUES["torso_height_factor"])),
        )

        cv2.ellipse(
            mask,
            torso_center,
            torso_axes,
            CONTROL_VALUES["ellipse_angle_start"],
            CONTROL_VALUES["ellipse_angle_start"],
            CONTROL_VALUES["ellipse_angle_end"],
            cv2.GC_PR_FGD,
            -1,
        )

        # Mark the inner face as definite foreground to protect facial details from being removed.
        inner_axes = (
            max(1, int(face_width * CONTROL_VALUES["inner_face_width_factor"])),
            max(1, int(face_width * CONTROL_VALUES["inner_face_height_factor"])),
        )

        cv2.ellipse(
            mask,
            head_center,
            inner_axes,
            CONTROL_VALUES["ellipse_angle_start"],
            CONTROL_VALUES["ellipse_angle_start"],
            CONTROL_VALUES["ellipse_angle_end"],
            cv2.GC_FGD,
            -1,
        )

        # Mark the central torso as definite foreground to keep the subject body connected.
        torso_seed_y = min(
            height - 1,
            max(0, int(center_y + face_width * CONTROL_VALUES["torso_seed_offset_factor"])),
        )

        cv2.ellipse(
            mask,
            (center_x, torso_seed_y),
            (
                max(1, int(face_width * CONTROL_VALUES["torso_seed_width_factor"])),
                max(1, int(face_width * CONTROL_VALUES["torso_seed_height_factor"])),
            ),
            CONTROL_VALUES["ellipse_angle_start"],
            CONTROL_VALUES["ellipse_angle_start"],
            CONTROL_VALUES["ellipse_angle_end"],
            cv2.GC_FGD,
            -1,
        )

        # Image edges provide reliable background seeds and help remove border artifacts.
        border = max(
            CONTROL_VALUES["minimum_border_size"],
            int(min(width, height) * CONTROL_VALUES["border_ratio"]),
        )

        # Mark only the top border as definite background
        border = max(2, int(min(width, height) * 0.01))

        mask[:border, :] = cv2.GC_BGD

        # Keep side and bottom borders as probable regions
        # so GrabCut can preserve shoulders and torso.

        # Run GrabCut using the initialized mask and control parameters.
        background_model = np.zeros((1, CONTROL_VALUES["grabcut_model_size"]), np.float64)
        foreground_model = np.zeros((1, CONTROL_VALUES["grabcut_model_size"]), np.float64)

        cv2.grabCut(
            image,
            mask,
            None,
            background_model,
            foreground_model,
            self.iterations,
            cv2.GC_INIT_WITH_MASK,
        )

        # Convert GrabCut labels into a binary alpha mask used as the transparency channel.
        alpha = np.where(
            (mask == cv2.GC_FGD) |
            (mask == cv2.GC_PR_FGD),
            CONTROL_VALUES["alpha_foreground"],
            CONTROL_VALUES["alpha_background"],
        ).astype(np.uint8)

        # Preserve only the largest foreground component to avoid small disconnected fragments.
        count, labels, stats, _ = (
            cv2.connectedComponentsWithStats(
                alpha,
                connectivity=CONTROL_VALUES["connected_components_connectivity"],
            )
        )

        if count > 1:
            largest = CONTROL_VALUES["largest_component_offset"] + np.argmax(
                stats[1:, cv2.CC_STAT_AREA]
            )
            alpha = np.where(
                labels == largest,
                CONTROL_VALUES["alpha_foreground"],
                CONTROL_VALUES["alpha_background"],
            ).astype(np.uint8)

        # Remove small white edge halos after segmentation.
        if self.erosion_size > 1:
            kernel = np.ones(
                (self.erosion_size, self.erosion_size),
                np.uint8,
            )
            alpha = cv2.erode(alpha, kernel)

        # Smooth edges to produce a cleaner cutout silhouette.
        if self.blur_size > 1:
            alpha = cv2.GaussianBlur(
                alpha,
                (self.blur_size, self.blur_size),
                0,
            )

        return alpha

    def remove_background(self, image):
        """Return a BGRA image with transparent background."""
        alpha = self.create_mask(image)

        result = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
        result[:, :, 3] = alpha

        return result
