
from pathlib import Path

from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QIcon
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
    QSlider,
)

from src.paths import get_resource_path
from src.worker_manager import WorkerManager


SUPPORTED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".bmp", ".webp"
}

def create_percentage_slider(default, minimum=0, maximum=100):
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setRange(minimum, maximum)
    slider.setValue(default)

    value_label = QLabel(f"{default}%")
    value_label.setMinimumWidth(45)
    value_label.setAlignment(Qt.AlignmentFlag.AlignRight)

    slider.valueChanged.connect(
        lambda value: value_label.setText(f"{value}%")
    )

    layout.addWidget(slider)
    layout.addWidget(value_label)

    return container, slider, value_label


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

        icon_path = get_resource_path("assets", "icons", "koh.png")
        self.setWindowIcon(QIcon(str(icon_path)))

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Header with app icon and branding
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 8)
        header_layout.setSpacing(12)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        icon_path = get_resource_path("assets", "icons", "koh.png")
        icon_label = QLabel()
        icon_label.setPixmap(QIcon(str(icon_path)).pixmap(42, 42))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        title_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        title = QLabel("KOH")
        title.setStyleSheet("font-size: 28px; font-weight: bold;")

        subtitle = QLabel("Keypoint-Oriented Harmonization")

        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)

        header_layout.addWidget(icon_label)
        header_layout.addLayout(title_layout)
        layout.addLayout(header_layout)

        # Input images
        input_group = QGroupBox("Input Images")
        input_group.setStyleSheet(
            "QGroupBox { border: 1px solid #cfcfcf; border-radius: 4px; margin-top: 12px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; font-weight: 700; font-size: 14px; }"
        )
        input_layout = QVBoxLayout()

        self.file_list = QListWidget()
        input_layout.addWidget(self.file_list)

        self.selection_status_label = QLabel("Nenhuma imagem selecionada")
        self.selection_status_label.setStyleSheet(
            "color: #444444; font-size: 11px; margin-top: 4px;"
        )
        input_layout.addWidget(self.selection_status_label)

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
        settings_group.setStyleSheet(
            "QGroupBox { border: 1px solid #cfcfcf; border-radius: 4px; margin-top: 12px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; font-weight: 700; font-size: 14px; }"
        )
        settings_layout = QFormLayout()

        self.width_input = QSpinBox()
        self.width_input.setRange(1, 10000)
        self.width_input.setValue(400)

        self.height_input = QSpinBox()
        self.height_input.setRange(1, 10000)
        self.height_input.setValue(400)

        face_widget, self.face_ratio_input, self.face_ratio_value_label = (
            create_percentage_slider(default=35, minimum=1)
        )

        x_widget, self.position_x_input, self.position_x_value_label = (
            create_percentage_slider(default=50)
        )

        y_widget, self.position_y_input, self.position_y_value_label = (
            create_percentage_slider(default=40)
        )

        settings_layout.addRow("Width:", self.width_input)
        settings_layout.addRow("Height:", self.height_input)
        settings_layout.addRow("Face Ratio:", face_widget)
        settings_layout.addRow("Position X:", x_widget)
        settings_layout.addRow("Position Y:", y_widget)

        self.background_input = QComboBox()

        self.background_input.addItem("Disabled", "none")
        self.background_input.addItem("Fast - White Background", "fast")
        self.background_input.addItem("AI - MODNet", "ai")

        settings_layout.addRow(
            "Background Removal:",
            self.background_input,
        )

        self.reset_defaults_button = QPushButton("Reset Defaults")
        self.reset_defaults_button.clicked.connect(self.reset_settings_to_defaults)
        settings_layout.addRow("", self.reset_defaults_button)

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
        self.status_label.setStyleSheet("font-size: 12px; color: #333333;")
        self.footer_label = QLabel(
            "<b>Autor:</b> Arthur Castro | "
            "GitHub: ArthurDCastro | "
            "Email: arthurdiasvianacastro@gmail.com"
        )
        self.footer_label.setTextFormat(Qt.TextFormat.RichText)
        self.footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.footer_label.setStyleSheet(
            "color: #666666; font-size: 11px;"
        )

        layout.addWidget(self.progress_bar)
        layout.addWidget(self.process_button)
        layout.addWidget(self.status_label)
        layout.addWidget(self.footer_label)

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

        if len(self.files) == 1:
            selected_text = "1 imagem selecionada"
        elif len(self.files) == 0:
            selected_text = "Nenhuma imagem selecionada"
        else:
            selected_text = f"{len(self.files)} imagens selecionadas"

        self.status_label.setText(selected_text)
        self.selection_status_label.setText(selected_text)

    def clear_images(self):
        self.files.clear()
        self.file_list.clear()
        self.status_label.setText("Nenhuma imagem selecionada")
        self.selection_status_label.setText("Nenhuma imagem selecionada")

    def reset_settings_to_defaults(self):
        self.width_input.setValue(400)
        self.height_input.setValue(400)
        self.face_ratio_input.setValue(35)
        self.position_x_input.setValue(50)
        self.position_y_input.setValue(40)
        self.background_input.setCurrentIndex(0)

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
