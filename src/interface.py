
from pathlib import Path
from collections import deque
import time

from PySide6.QtCore import QThread, QTimer, Signal, Qt
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
    QAbstractItemView,
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
    progress = Signal(int, int, float)
    image_started = Signal(str)
    image_failed = Signal(dict)
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
                started_callback=self.report_started,
                error_callback=self.image_failed.emit,
            )

            self.completed.emit(results)

        except Exception as error:
            self.failed.emit(str(error))

    def report_progress(self, current, total):
        self.progress.emit(current, total, time.monotonic() - self.image_start)

    def report_started(self, filename):
        self.image_start = time.monotonic()
        self.image_started.emit(filename)



class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.files = []
        self.output_dir = None
        self.worker = None
        self.batch_start = None
        self.image_start = None
        self.completed_images = 0
        self.total_images = 0
        self.image_durations = deque(maxlen=10)
        self.elapsed_seconds = 0.0
        self.progress_timer = QTimer(self)
        self.progress_timer.setInterval(1000)
        self.progress_timer.timeout.connect(self.update_time)

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
        self.file_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.file_list.itemSelectionChanged.connect(self.update_remove_button)
        self.file_list.setToolTip("Use Ctrl/Cmd or Shift to select multiple images to remove.")
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
        self.remove_button = QPushButton("Remove Selected")
        self.remove_button.setEnabled(False)

        self.add_files_button.clicked.connect(self.add_images)
        self.add_folder_button.clicked.connect(self.add_folder)
        self.clear_button.clicked.connect(self.clear_images)
        self.remove_button.clicked.connect(self.remove_selected_images)

        buttons_layout.addWidget(self.add_files_button)
        buttons_layout.addWidget(self.add_folder_button)
        buttons_layout.addWidget(self.remove_button)
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
        self.progress_bar.setFormat("%p%")
        self.count_label = QLabel("Processed: 0 / 0")
        self.filename_label = QLabel("Current image: —")
        self.filename_label.setTextFormat(Qt.TextFormat.PlainText)
        self.filename_label.setWordWrap(True)
        self.time_label = QLabel("Elapsed: 00:00:00 | Remaining: Calculating...")
        self.error_count_label = QLabel("Images with errors: 0")
        self.error_list = QListWidget()
        self.error_list.setMaximumHeight(110)
        self.error_list.setWordWrap(True)

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
        layout.addWidget(self.count_label)
        layout.addWidget(self.filename_label)
        layout.addWidget(self.time_label)
        layout.addWidget(self.error_count_label)
        layout.addWidget(self.error_list)
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

        self.update_selection_status()

    def update_selection_status(self):
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
        self.update_selection_status()

    def update_remove_button(self):
        self.remove_button.setEnabled(
            self.file_list.isEnabled() and bool(self.file_list.selectedItems())
        )

    def remove_selected_images(self):
        if not self.file_list.isEnabled():
            return
        rows = sorted(
            (self.file_list.row(item) for item in self.file_list.selectedItems()),
            reverse=True,
        )
        if not rows:
            return
        for row in rows:
            self.file_list.takeItem(row)
            self.files.pop(row)
        self.update_selection_status()
        self.update_remove_button()

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
        if self.worker is not None and self.worker.isRunning():
            return
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
        self.file_list.setEnabled(False)
        self.remove_button.setEnabled(False)
        self.output_button.setEnabled(False)

        self.status_label.setText("Processing...")
        self.completed_images = 0
        self.total_images = len(self.files)
        self.image_durations.clear()
        self.error_list.clear()
        self.error_count_label.setText("Images with errors: 0")
        self.update_progress_color()
        self.batch_start = time.monotonic()
        self.image_start = None
        self.elapsed_seconds = 0.0
        self.count_label.setText(f"Processed: 0 / {self.total_images}")
        self.filename_label.setText("Current image: —")
        self.update_time()
        self.progress_timer.start()

        self.worker = ProcessingWorker(
            files=self.files.copy(),
            output_dir=self.output_dir,
            settings=settings,
        )

        self.worker.progress.connect(self.update_progress)
        self.worker.image_started.connect(self.update_filename)
        self.worker.image_failed.connect(self.add_image_error)
        self.worker.completed.connect(self.processing_completed)
        self.worker.failed.connect(self.processing_failed)

        self.worker.start()

    def add_image_error(self, error):
        self.error_list.addItem(f"{Path(error['file']).name}: {error['error']}")
        self.error_list.item(self.error_list.count() - 1).setToolTip(
            f"{error['file']}\n{error['error']}"
        )
        self.error_count_label.setText(f"Images with errors: {self.error_list.count()}")
        self.error_list.scrollToBottom()
        self.update_progress_color()

    def update_progress_color(self, errors=None, total=None, failed=False):
        errors = self.error_list.count() if errors is None else errors
        total = self.total_images if total is None else total
        if failed or (total > 0 and errors == total):
            color = "#C96379"  # Muted raspberry red complements purple.
            description = "Processing failed" if failed else "All images failed"
        elif errors:
            color = "#D6A34A"  # Warm amber for partial failures.
            description = "Some images failed"
        else:
            self.progress_bar.setStyleSheet("")
            self.progress_bar.setToolTip("")
            return
        self.progress_bar.setStyleSheet(
            "QProgressBar { border: 1px solid palette(mid); border-radius: 4px;"
            " background: palette(base); color: palette(text); text-align: center; }"
            f"QProgressBar::chunk {{ background-color: {color}; border-radius: 3px; }}"
        )
        self.progress_bar.setToolTip(description)

    def update_filename(self, filename):
        self.image_start = time.monotonic()
        self.filename_label.setText(f"Current image: {Path(filename).name}")
        self.filename_label.setToolTip(filename)

    def update_progress(self, current, total, duration):
        self.completed_images = current
        self.image_durations.append(duration)
        self.image_start = None
        percentage = int(current / total * 100)
        self.progress_bar.setValue(percentage)
        self.count_label.setText(f"Processed: {current} / {total}")
        self.update_time()

        self.status_label.setText(
            f"Processing {current}/{total}"
        )

    @staticmethod
    def format_duration(seconds):
        seconds = max(0, int(seconds))
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def update_time(self):
        if self.batch_start is None:
            return
        now = time.monotonic()
        self.elapsed_seconds = now - self.batch_start
        remaining = "Calculating..."
        if self.completed_images == self.total_images:
            remaining = self.format_duration(0)
        elif len(self.image_durations) >= 2:
            average = sum(self.image_durations) / len(self.image_durations)
            current_elapsed = now - self.image_start if self.image_start is not None else 0
            estimate = average * (self.total_images - self.completed_images - 1)
            estimate += max(0, average - current_elapsed)
            remaining = self.format_duration(estimate)
        self.time_label.setText(
            f"Elapsed: {self.format_duration(self.elapsed_seconds)} | Remaining: {remaining}"
        )

    def stop_timing(self, failed=False):
        self.progress_timer.stop()
        self.update_time()
        self.filename_label.setText("Current image: —")
        self.filename_label.setToolTip("")
        self.time_label.setText(
            f"Duration: {self.format_duration(self.elapsed_seconds)}"
            + (" | Processing failed" if failed else "")
        )

    def processing_completed(self, results):
        self.stop_timing()
        self.reset_controls()

        success = results["success"]
        errors = len(results["errors"])
        self.update_progress_color(errors=errors, total=results["total"])

        self.status_label.setText(
            f"Completed: {success} successful, {errors} errors"
        )

        message = (
            f"Total: {results['total']}\n"
            f"Success: {success}\n"
            f"Errors: {errors}\n"
            f"Duration: {self.format_duration(self.elapsed_seconds)}"
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
        self.update_progress_color(failed=True)
        self.stop_timing(failed=True)
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
        self.file_list.setEnabled(True)
        self.update_remove_button()
        self.output_button.setEnabled(True)
