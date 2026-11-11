"""Bounded, asynchronous image previews using the isolated processing worker."""
from collections import OrderedDict
from pathlib import Path
import tempfile
import threading

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, Signal, QSize
from PySide6.QtGui import QColor, QImageReader, QPainter, QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsView, QGraphicsScene, QGroupBox,
)

from src.worker_manager import WorkerManager, ProcessingCancelled


THUMBNAIL_SIZE = 1024
CACHE_SIZE = 8


def image_key(path):
    path = Path(path)
    stat = path.stat()
    return str(path), stat.st_mtime_ns, stat.st_size


def settings_key(settings):
    return tuple(sorted(settings.items()))


def load_thumbnail(path):
    reader = QImageReader(str(path))
    # Match OpenCV's EXIF orientation handling while preserving PNG alpha.
    reader.setAutoTransform(True)
    size = reader.size()
    if size.isValid() and max(size.width(), size.height()) > THUMBNAIL_SIZE:
        reader.setScaledSize(size.scaled(
            QSize(THUMBNAIL_SIZE, THUMBNAIL_SIZE), Qt.AspectRatioMode.KeepAspectRatio
        ))
    image = reader.read()
    if image.isNull():
        raise ValueError(reader.errorString() or "Unable to load image")
    if max(image.width(), image.height()) > THUMBNAIL_SIZE:
        image = image.scaled(
            THUMBNAIL_SIZE, THUMBNAIL_SIZE, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    return image


def process_preview(file, settings, cancel_event=None):
    # Keep model execution, timeouts and memory limits identical to a batch.
    with tempfile.TemporaryDirectory(prefix="koh_preview_") as directory:
        result = WorkerManager(cancel_event=cancel_event).process_image(file, directory, settings)
        if result.get("cancelled"):
            raise ProcessingCancelled()
        if not result["success"]:
            raise ValueError(result["error"])
        return load_thumbnail(result["output"])


class TaskSignals(QObject):
    done = Signal(object)


class PreviewTask(QRunnable):
    def __init__(self, key, operation):
        super().__init__()
        self.setAutoDelete(False)
        self.key = key
        self.operation = operation
        self.signals = TaskSignals()

    def run(self):
        try:
            image = self.operation()
            error = None
        except ProcessingCancelled as exception:
            image = None
            error = exception
        except Exception as exception:
            image = None
            error = str(exception)
        self.signals.done.emit((self.key, image, error))


class ImageView(QGraphicsView):
    """Aspect-preserving image view with a checkerboard behind transparent pixels."""
    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setMinimumSize(180, 220)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.fitting = True
        self.has_image = False
        self.zoom_factor = 1.0
        tile = QPixmap(24, 24)
        tile.fill(QColor("#eeeeee"))
        painter = QPainter(tile)
        painter.fillRect(0, 0, 12, 12, QColor("#cccccc"))
        painter.fillRect(12, 12, 12, 12, QColor("#cccccc"))
        painter.end()
        self.setBackgroundBrush(tile)

    def set_image(self, image):
        self.scene().clear()
        self.has_image = image is not None and not image.isNull()
        self.resetTransform()
        if self.has_image:
            item = self.scene().addPixmap(QPixmap.fromImage(image))
            self.scene().setSceneRect(item.boundingRect())
        else:
            self.scene().setSceneRect(0, 0, 1, 1)
        self.fit_image()

    def fit_image(self):
        self.fitting = True
        self.zoom_factor = 1.0
        if self.has_image:
            self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def zoom(self, factor):
        if self.has_image and 0.25 <= self.zoom_factor * factor <= 16:
            self.fitting = False
            self.zoom_factor *= factor
            self.scale(factor, factor)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.fitting:
            self.fit_image()


class PreviewPanel(QGroupBox):
    navigate = Signal(int)
    busy_changed = Signal(bool)

    def __init__(self, get_settings, parent=None):
        super().__init__("Image Preview", parent)
        self.get_settings = get_settings
        self.files = []
        self.index = -1
        self.cache = OrderedDict()
        self.preview_errors = OrderedDict()
        self.revision = 0
        self.results = {}
        self.jobs = {}
        self.wanted = {}
        self.messages = {}
        self.busy = False
        self.cancel_event = threading.Event()
        self.batch_active = False
        self.validation_states = None
        self.load_pool = QThreadPool(self)
        self.load_pool.setMaxThreadCount(1)
        self.process_pool = QThreadPool(self)
        self.process_pool.setMaxThreadCount(1)

        layout = QVBoxLayout(self)
        self.caption = QLabel("Select an image")
        self.caption.setTextFormat(Qt.TextFormat.PlainText)
        self.caption.setWordWrap(True)
        layout.addWidget(self.caption)
        views = QHBoxLayout()
        self.original = ImageView()
        self.processed = ImageView()
        self.original_status = QLabel("No image selected")
        self.processed_status = QLabel("No output yet")
        for title, view, status in (
            ("Original", self.original, self.original_status),
            ("Processed", self.processed, self.processed_status),
        ):
            column = QVBoxLayout()
            column.addWidget(QLabel(title))
            column.addWidget(view, 1)
            status.setTextFormat(Qt.TextFormat.PlainText)
            status.setWordWrap(True)
            column.addWidget(status)
            views.addLayout(column, 1)
        layout.addLayout(views, 1)
        navigation = QHBoxLayout()
        self.previous_button = QPushButton("Previous")
        self.next_button = QPushButton("Next")
        self.preview_button = QPushButton("Preview Image")
        self.previous_button.clicked.connect(lambda: self.move(-1))
        self.next_button.clicked.connect(lambda: self.move(1))
        self.preview_button.clicked.connect(self.generate)
        for button in (self.previous_button, self.next_button, self.preview_button):
            navigation.addWidget(button)
        layout.addLayout(navigation)
        zoom = QHBoxLayout()
        for title, callback in (("−", lambda: self.zoom(0.8)),
                                ("Fit", self.fit), ("+", lambda: self.zoom(1.25))):
            button = QPushButton(title)
            button.clicked.connect(callback)
            zoom.addWidget(button)
        layout.addLayout(zoom)
        hint = QLabel("Preview Image uses current settings without saving to your output folder.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.update_buttons()

    @property
    def current_file(self):
        return self.files[self.index] if 0 <= self.index < len(self.files) else None

    def set_files(self, files):
        current = self.current_file
        old_index = self.index
        self.files = list(files)
        self.results = {file: result for file, result in self.results.items() if file in self.files}
        index = self.files.index(current) if current in self.files else min(max(old_index, 0), len(self.files) - 1)
        self.select(index)

    def select(self, index):
        # Drop obsolete queued decodes when the user browses quickly.
        for key, task in list(self.jobs.items()):
            if key[0] == "disk" and self.load_pool.tryTake(task):
                self.jobs.pop(key)
        self.index = index if 0 <= index < len(self.files) else -1
        self.wanted.clear()
        self.messages.clear()
        self.original.set_image(None)
        self.processed.set_image(None)
        self.update_buttons()
        file = self.current_file
        if file is None:
            self.caption.setText("Select an image")
            self.original_status.setText("No image selected")
            self.processed_status.setText("No output yet")
            return
        self.caption.setText(f"{self.index + 1} / {len(self.files)} — {Path(file).name}")
        self.caption.setToolTip(file)
        state = self.input_state()
        if state is not None and state.get("valid") is not True:
            self.original_status.setText(state.get("error", "Checking image..."))
        else:
            self.request_image("original", file, "Original")
        self.show_result()

    def move(self, delta):
        index = self.index + delta
        if 0 <= index < len(self.files):
            self.select(index)
            self.navigate.emit(index)

    def update_buttons(self):
        self.previous_button.setEnabled(self.index > 0)
        self.next_button.setEnabled(0 <= self.index < len(self.files) - 1)
        state = self.input_state()
        allowed = state is None or state.get("valid") is True
        self.preview_button.setEnabled(self.current_file is not None and allowed and not self.busy and not self.batch_active)

    def input_state(self):
        if self.validation_states is not None:
            return self.validation_states.get(self.current_file, {"valid": None, "error": "Checking image..."})
        return None

    def request_image(self, side, path, message):
        try:
            key = ("disk", self.revision, *image_key(path))
        except OSError as error:
            self.status(side).setText(f"Unable to load image: {error}")
            return
        self.messages[side] = message
        self.wanted[side] = key
        self.status(side).setText("Loading...")
        self.request(key, lambda: load_thumbnail(path))

    def status(self, side):
        return self.original_status if side == "original" else self.processed_status

    def request(self, key, operation, processing=False):
        if key in self.cache:
            image = self.cache[key]
            self.cache.move_to_end(key)
            self.display(key, image, None)
        elif key not in self.jobs:
            task = PreviewTask(key, operation)
            task.signals.done.connect(self.task_finished)
            self.jobs[key] = task
            (self.process_pool if processing else self.load_pool).start(task)

    def task_finished(self, result):
        key, image, error = result
        self.jobs.pop(key, None)
        if key[0] == "preview" and (self.cancel_event.is_set() or isinstance(error, ProcessingCancelled)):
            image, error = None, None
            self.messages["processed"] = "Preview cancelled"
        if image is not None:
            self.cache[key] = image
            self.cache.move_to_end(key)
            while len(self.cache) > CACHE_SIZE:
                self.cache.popitem(last=False)
        if key[0] == "preview":
            if error:
                self.preview_errors[key] = error
                while len(self.preview_errors) > CACHE_SIZE:
                    self.preview_errors.popitem(last=False)
            self.busy = False
            self.busy_changed.emit(False)
            self.update_buttons()
        self.display(key, image, error)

    def display(self, key, image, error):
        for side in ("original", "processed"):
            if self.wanted.get(side) == key:
                view = self.original if side == "original" else self.processed
                view.set_image(image)
                self.status(side).setText(
                    f"Preview failed: {error}" if error else self.messages.get(side, "Preview")
                )

    def preview_key(self):
        return ("preview", *image_key(self.current_file), settings_key(self.get_settings()))

    def show_result(self):
        file = self.current_file
        self.wanted.pop("processed", None)
        self.processed.set_image(None)
        if file is None:
            return
        state = self.input_state()
        key = None
        if state is None or state.get("valid") is True:
            try:
                key = self.preview_key()
            except OSError:
                pass
        if not self.batch_active and key in self.cache:
            self.wanted["processed"] = key
            self.messages["processed"] = "Preview — current settings"
            self.request(key, None)
            return
        if key in self.jobs:
            self.wanted["processed"] = key
            self.messages["processed"] = "Preview — current settings"
            self.processed_status.setText("Generating preview...")
            return
        if not self.batch_active and key in self.preview_errors:
            self.processed_status.setText(f"Preview failed: {self.preview_errors[key]}")
            return
        result = self.results.get(file)
        if result is None:
            self.processed_status.setText("No output yet — click Preview Image")
        elif result.get("pending"):
            self.processed_status.setText("Waiting for batch result...")
        elif not result["success"]:
            self.processed_status.setText(f"Processing failed: {result['error']}")
        else:
            message = "Saved batch result"
            if result.get("settings") != self.get_settings():
                message += " — settings have changed"
            self.request_image("processed", result["output"], message)

    def generate(self):
        if self.busy or self.batch_active or self.current_file is None:
            return
        state = self.input_state()
        if state is not None and state.get("valid") is not True:
            self.processed_status.setText(state.get("error", "Checking image..."))
            return
        try:
            key = self.preview_key()
        except OSError as error:
            self.processed_status.setText(f"Preview failed: {error}")
            return
        self.wanted["processed"] = key
        self.preview_errors.pop(key, None)
        self.messages["processed"] = "Preview — current settings"
        self.processed.set_image(None)
        self.processed_status.setText("Generating preview...")
        if key not in self.cache:
            self.cancel_event = threading.Event()
            self.busy = True
            self.busy_changed.emit(True)
            self.update_buttons()
        file, settings = self.current_file, self.get_settings().copy()
        cancel_event = self.cancel_event
        self.request(key, lambda: process_preview(file, settings, cancel_event), processing=True)

    def cancel(self):
        if self.busy:
            self.cancel_event.set()

    def settings_changed(self):
        self.show_result()

    def begin_batch(self, files):
        self.batch_active = True
        for file in files:
            self.results[file] = {"pending": True}
        # A new batch must show fresh outputs, even at the same output path.
        self.cache.clear()
        self.preview_errors.clear()
        self.revision += 1
        self.show_result()
        self.update_buttons()

    def record_result(self, result):
        if result["file"] in self.files:
            self.results[result["file"]] = result
            if result["file"] == self.current_file:
                self.show_result()

    def end_batch(self, cancelled=False):
        self.batch_active = False
        for file, result in list(self.results.items()):
            if result.get("pending"):
                self.results[file] = {"success": False, "error": "Not processed — batch cancelled" if cancelled else "No output — batch interrupted"}
        self.show_result()
        self.update_buttons()

    def zoom(self, factor):
        self.original.zoom(factor)
        self.processed.zoom(factor)

    def fit(self):
        self.original.fit_image()
        self.processed.fit_image()
