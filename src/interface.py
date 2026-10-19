
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QSpinBox,
    QDoubleSpinBox,
    QProgressBar,
    QMessageBox,
    QListWidget,
    QGroupBox,
    QFormLayout,
    QComboBox,
)

from src.worker_manager import WorkerManager


SUPPORTED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".bmp", ".webp"
}



class ProcessingWorker(QThread):
    progress = Signal(int, int)
    completed = Signal(dict)
    failed = Signal(str)

    def __init__(self, files, output_dir, settings):
        super().__init__()

        self.files = files
        self.output_dir = output_dir
        self.settings = settings

    def run(self):
        try:
            manager = WorkerManager(
                max_memory_mb=4096,
                max_time_seconds=120,
                check_interval=0.2,
            )

            results = manager.process_batch(
                files=self.files,
                output_dir=self.output_dir,
                settings=self.settings,
                callback=self.report_progress,
            )

            self.completed.emit(results)

        except Exception as error:
            self.failed.emit(str(error))

    def report_progress(self, current, total):
        self.progress.emit(current, total)



class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.files = []
        self.output_dir = None
        self.worker = None

        self.setWindowTitle("KOH - Face Alignment")
        self.resize(650, 650)

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("KOH")
        title.setStyleSheet(
            "font-size: 28px; font-weight: bold;"
        )

        subtitle = QLabel(
            "Keypoint-Oriented Harmonization"
        )

        layout.addWidget(title)
        layout.addWidget(subtitle)

        # Input images
        input_group = QGroupBox("Input Images")
        input_layout = QVBoxLayout()

        self.file_list = QListWidget()
        input_layout.addWidget(self.file_list)

        buttons_layout = QHBoxLayout()

        self.add_files_button = QPushButton("Add Images")
        self.add_folder_button = QPushButton("Add Folder")
        self.clear_button = QPushButton("Clear")

        self.add_files_button.clicked.connect(self.add_images)
        self.add_folder_button.clicked.connect(self.add_folder)
        self.clear_button.clicked.connect(self.clear_images)

        buttons_layout.addWidget(self.add_files_button)
        buttons_layout.addWidget(self.add_folder_button)
        buttons_layout.addWidget(self.clear_button)

        input_layout.addLayout(buttons_layout)
        input_group.setLayout(input_layout)

        layout.addWidget(input_group)

        # Output settings
        settings_group = QGroupBox("Output Settings")
        settings_layout = QFormLayout()

        self.width_input = QSpinBox()
        self.width_input.setRange(1, 10000)
        self.width_input.setValue(600)

        self.height_input = QSpinBox()
        self.height_input.setRange(1, 10000)
        self.height_input.setValue(800)

        self.face_ratio_input = QDoubleSpinBox()
        self.face_ratio_input.setRange(1, 100)
        self.face_ratio_input.setValue(40)
        self.face_ratio_input.setSuffix(" %")

        self.position_x_input = QDoubleSpinBox()
        self.position_x_input.setRange(0, 100)
        self.position_x_input.setValue(50)
        self.position_x_input.setSuffix(" %")

        self.position_y_input = QDoubleSpinBox()
        self.position_y_input.setRange(0, 100)
        self.position_y_input.setValue(40)
        self.position_y_input.setSuffix(" %")

        settings_layout.addRow("Width:", self.width_input)
        settings_layout.addRow("Height:", self.height_input)
        settings_layout.addRow(
            "Face Ratio:", self.face_ratio_input
        )
        settings_layout.addRow(
            "Position X:", self.position_x_input
        )
        settings_layout.addRow(
            "Position Y:", self.position_y_input
        )
        self.background_input = QComboBox()

        self.background_input.addItem("Disabled", "none")
        self.background_input.addItem("Fast - White Background", "fast")
        self.background_input.addItem("AI - U2NetP", "ai")

        settings_layout.addRow(
            "Background Removal:",
            self.background_input,
        )

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # Output directory
        output_layout = QHBoxLayout()

        self.output_label = QLabel(
            "No output directory selected"
        )

        self.output_button = QPushButton("Browse")
        self.output_button.clicked.connect(
            self.select_output_directory
        )

        output_layout.addWidget(self.output_label, 1)
        output_layout.addWidget(self.output_button)

        layout.addLayout(output_layout)

        # Processing
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)

        self.process_button = QPushButton("Process Images")
        self.process_button.clicked.connect(
            self.start_processing
        )

        self.status_label = QLabel("Ready")

        layout.addWidget(self.progress_bar)
        layout.addWidget(self.process_button)
        layout.addWidget(self.status_label)

    def add_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Images",
            "",
            "Images (*.jpg *.jpeg *.png *.bmp *.webp)"
        )

        self.append_files(files)

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Image Folder"
        )

        if not folder:
            return

        files = [
            str(file)
            for file in sorted(Path(folder).iterdir())
            if file.is_file()
            and file.suffix.lower() in SUPPORTED_EXTENSIONS
        ]

        self.append_files(files)

    def append_files(self, files):
        for file in files:
            file = str(Path(file).resolve())

            if file not in self.files:
                self.files.append(file)
                self.file_list.addItem(file)

        self.status_label.setText(
            f"{len(self.files)} images selected"
        )

    def clear_images(self):
        self.files.clear()
        self.file_list.clear()
        self.status_label.setText("Ready")

    def select_output_directory(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory"
        )

        if folder:
            self.output_dir = folder
            self.output_label.setText(folder)

    def start_processing(self):
        if not self.files:
            QMessageBox.warning(
                self,
                "Warning",
                "Please select at least one image."
            )
            return

        if not self.output_dir:
            QMessageBox.warning(
                self,
                "Warning",
                "Please select an output directory."
            )
            return

        settings = {
            "width": self.width_input.value(),
            "height": self.height_input.value(),
            "face_ratio": (
                self.face_ratio_input.value() / 100
            ),
            "position_x": (
                self.position_x_input.value() / 100
            ),
            "position_y": (
                self.position_y_input.value() / 100
            ),
            "background_mode": self.background_input.currentData(),
        }

        self.progress_bar.setValue(0)
        self.process_button.setEnabled(False)
        self.add_files_button.setEnabled(False)
        self.add_folder_button.setEnabled(False)
        self.clear_button.setEnabled(False)
        self.output_button.setEnabled(False)

        self.status_label.setText("Processing...")

        self.worker = ProcessingWorker(
            files=self.files.copy(),
            output_dir=self.output_dir,
            settings=settings,
        )

        self.worker.progress.connect(self.update_progress)
        self.worker.completed.connect(self.processing_completed)
        self.worker.failed.connect(self.processing_failed)

        self.worker.start()

    def update_progress(self, current, total):
        percentage = int(current / total * 100)
        self.progress_bar.setValue(percentage)

        self.status_label.setText(
            f"Processing {current}/{total}"
        )

    def processing_completed(self, results):
        self.reset_controls()

        success = results["success"]
        errors = len(results["errors"])

        self.status_label.setText(
            f"Completed: {success} successful, {errors} errors"
        )

        message = (
            f"Total: {results['total']}\n"
            f"Success: {success}\n"
            f"Errors: {errors}"
        )

        if errors:
            details = "\n".join(
                f"{item['file']}: {item['error']}"
                for item in results["errors"]
            )

            dialog = QMessageBox(self)
            dialog.setWindowTitle("Processing Results")
            dialog.setText(message)
            dialog.setDetailedText(details)
            dialog.setIcon(QMessageBox.Icon.Warning)
            dialog.exec()
        else:
            QMessageBox.information(
                self,
                "Processing Results",
                message
            )

    def processing_failed(self, error):
        self.reset_controls()
        self.status_label.setText("Processing failed")

        QMessageBox.critical(
            self,
            "Error",
            error
        )

    def reset_controls(self):
        self.process_button.setEnabled(True)
        self.add_files_button.setEnabled(True)
        self.add_folder_button.setEnabled(True)
        self.clear_button.setEnabled(True)
        self.output_button.setEnabled(True)
