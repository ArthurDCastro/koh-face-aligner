
import sys
from src.version import APP_NAME, VERSION


def main():
    if "--version" in sys.argv[1:] or "-V" in sys.argv[1:]:
        print(f"{APP_NAME} {VERSION}")
        return 0

    if "--koh-validator" in sys.argv:
        sys.argv.remove("--koh-validator")
        from src.validation import main as validation_main
        return validation_main()

    # Internal worker mode
    if "--koh-worker" in sys.argv:
        sys.argv.remove("--koh-worker")

        from src.worker import main as worker_main

        return worker_main()

    # Desktop application mode
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QIcon

    from src.interface import MainWindow
    from src.paths import get_resource_path

    # Create a single QApplication instance
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(VERSION)
    app.setOrganizationName("Arthur Castro")

    # Set application icon
    icon_path = get_resource_path(
        "assets", "icons", "koh.png"
    )
    app.setWindowIcon(QIcon(str(icon_path)))

    # Create and display the main window
    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
