
import sys


def main():
    # Internal worker mode
    if "--koh-worker" in sys.argv:
        sys.argv.remove("--koh-worker")

        from src.worker import main as worker_main

        return worker_main()

    # Desktop application mode
    from PySide6.QtWidgets import QApplication
    from src.interface import MainWindow

    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
