
import sys
from pathlib import Path


def get_resource_path(*parts):
    """Resolve bundled resources in source and frozen modes."""
    if getattr(sys, "frozen", False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parent.parent

    return base_path.joinpath(*parts)
