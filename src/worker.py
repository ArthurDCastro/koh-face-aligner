
import argparse
import json
import sys
from pathlib import Path

from src.processing import ImageProcessor


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--width", type=int, required=True)
    parser.add_argument("--height", type=int, required=True)
    parser.add_argument("--face-ratio", type=float, required=True)
    parser.add_argument("--position-x", type=float, default=0.5)
    parser.add_argument("--position-y", type=float, default=0.5)
    parser.add_argument(
        "--background-mode",
        choices=["none", "fast", "ai"],
        default="fast",
    )

    args = parser.parse_args()

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        processor = ImageProcessor()

        result = processor.process(
            files=[args.input],
            output_dir=args.output,
            width=args.width,
            height=args.height,
            face_ratio=args.face_ratio,
            position_x=args.position_x,
            position_y=args.position_y,
            background_mode=args.background_mode,
        )

        report_path.write_text(
            json.dumps(result, indent=2),
            encoding="utf-8",
        )

        return 0 if result["success"] == 1 else 1

    except Exception as error:
        report_path.write_text(
            json.dumps({"error": str(error)}),
            encoding="utf-8",
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
