
import sys


def main():
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
