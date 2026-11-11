"""Headless GUI tests for asynchronous preview state and image rendering."""
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from src.interface import MainWindow
from src.preview import CACHE_SIZE, PreviewPanel, load_thumbnail, process_preview
from src.paths import get_output_path
from src.worker_manager import WorkerManager


def wait_for(app, predicate, timeout=5):
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > deadline:
            raise AssertionError("Timed out waiting for preview")
        app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 20)
        time.sleep(0.005)
    app.processEvents()


class PreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.files = []
        for name, color in (("a.png", "#80ff0000"), ("b.png", "#ff00ff00")):
            path = Path(self.directory.name) / name
            image = QImage(2400, 1200, QImage.Format.Format_ARGB32)
            image.fill(QColor(color))
            self.assertTrue(image.save(str(path)))
            self.files.append(str(path))
        self.settings = {"width": 400, "height": 400, "face_ratio": 0.35,
                         "position_x": 0.5, "position_y": 0.4, "background_mode": "none"}
        self.panel = PreviewPanel(lambda: self.settings.copy())
        self.panel.resize(600, 450)
        self.panel.show()
        self.panel.set_files(self.files)
        self.drain()

    def drain(self):
        wait_for(self.app, lambda: not self.panel.jobs)

    def tearDown(self):
        self.panel.load_pool.waitForDone()
        self.panel.process_pool.waitForDone()
        self.app.processEvents()
        self.panel.close()

    def test_thumbnail_retains_aspect_ratio_and_alpha(self):
        image = load_thumbnail(self.files[0])
        self.assertEqual((image.width(), image.height()), (1024, 512))
        self.assertTrue(image.hasAlphaChannel())
        self.assertEqual(image.pixelColor(0, 0).alpha(), 128)
        self.assertTrue(self.panel.original.has_image)
        self.assertIn("1 / 2", self.panel.caption.text())
        # The background is a checkerboard texture, independent of the image.
        texture = self.panel.original.backgroundBrush().texture().toImage()
        self.assertNotEqual(texture.pixelColor(0, 0), texture.pixelColor(12, 0))
        self.panel.zoom(1.25)
        self.assertFalse(self.panel.original.fitting)
        self.panel.fit()
        self.assertTrue(self.panel.original.fitting)
        transform = self.panel.original.transform()
        self.assertAlmostEqual(transform.m11(), transform.m22())

    def test_generate_navigate_cache_and_settings_invalidation(self):
        image = load_thumbnail(self.files[0])
        release = threading.Event()
        started = threading.Event()
        received = []

        def process(file, settings):
            received.append((file, settings))
            started.set()
            release.wait(3)
            return image

        with patch("src.preview.process_preview", side_effect=process) as process_mock:
            try:
                self.panel.generate()
                wait_for(self.app, started.is_set)
                self.assertTrue(self.panel.busy)
                self.assertFalse(self.panel.preview_button.isEnabled())
                # GUI events and navigation continue while a model is running.
                ticks = []
                QTimer.singleShot(0, lambda: ticks.append(True))
                self.panel.move(1)
                wait_for(self.app, lambda: bool(ticks))
                self.assertIn("2 / 2", self.panel.caption.text())
            finally:
                release.set()
            self.drain()
            self.assertFalse(self.panel.processed.has_image)  # No stale image A in pane B.
            self.panel.move(-1)
            self.drain()
            self.assertTrue(self.panel.processed.has_image)
            self.panel.generate()
            self.assertEqual(process_mock.call_count, 1)
            self.assertEqual(received, [(self.files[0], self.settings)])
            self.settings["width"] = 600
            self.panel.settings_changed()
            self.assertFalse(self.panel.processed.has_image)
            self.panel.generate()
            self.drain()
            self.assertEqual(process_mock.call_count, 2)
            self.assertEqual(received[-1][1]["width"], 600)

    def test_batch_updates_failure_missing_output_and_interruption(self):
        self.panel.begin_batch(self.files)
        self.assertFalse(self.panel.preview_button.isEnabled())
        self.assertIn("Waiting", self.panel.processed_status.text())
        result = {"file": self.files[0], "success": True, "output": self.files[1],
                  "settings": self.settings.copy()}
        self.panel.record_result(result)
        self.drain()
        self.assertTrue(self.panel.processed.has_image)
        self.settings["height"] = 300
        self.panel.settings_changed()
        self.assertIn("settings have changed", self.panel.processed_status.text())
        self.panel.move(1)
        self.panel.record_result({"file": self.files[1], "success": False, "error": "No faces detected"})
        self.assertIn("No faces detected", self.panel.processed_status.text())
        self.assertFalse(self.panel.processed.has_image)
        self.panel.end_batch()
        self.assertTrue(self.panel.preview_button.isEnabled())
        self.panel.move(-1)
        Path(self.files[1]).unlink()
        self.panel.show_result()
        self.assertIn("Unable to load", self.panel.processed_status.text())
        self.assertFalse(self.panel.processed.has_image)
        self.panel.begin_batch(self.files)
        self.panel.end_batch()
        self.assertIn("batch interrupted", self.panel.processed_status.text())

    def test_preview_error_is_visible_and_retryable(self):
        with patch("src.preview.process_preview", side_effect=ValueError("Processing timeout")):
            self.panel.generate()
            self.drain()
        self.assertFalse(self.panel.busy)
        self.assertIn("Processing timeout", self.panel.processed_status.text())
        self.panel.move(1)
        self.panel.move(-1)
        self.assertIn("Processing timeout", self.panel.processed_status.text())
        with patch("src.preview.process_preview", return_value=load_thumbnail(self.files[0])):
            self.panel.generate()
            self.drain()
        self.assertTrue(self.panel.processed.has_image)

    def test_settings_changed_during_processing_hide_stale_preview(self):
        image = load_thumbnail(self.files[0])
        release = threading.Event()

        def process(file, settings):
            release.wait(3)
            return image

        with patch("src.preview.process_preview", side_effect=process):
            try:
                self.panel.generate()
                self.settings["width"] = 800
                self.panel.settings_changed()
            finally:
                release.set()
            self.drain()
        self.assertFalse(self.panel.processed.has_image)
        self.settings["width"] = 400
        self.panel.settings_changed()
        self.assertTrue(self.panel.processed.has_image)

    def test_cache_is_bounded_and_removed_selection_is_cleared(self):
        image = load_thumbnail(self.files[0])
        for index in range(CACHE_SIZE + 3):
            self.panel.task_finished((("disk", index), image, None))
        self.assertEqual(len(self.panel.cache), CACHE_SIZE)
        self.panel.set_files([self.files[1]])
        self.drain()
        self.assertEqual(self.panel.current_file, self.files[1])
        self.panel.set_files([])
        self.assertFalse(self.panel.original.has_image)
        self.assertFalse(self.panel.processed.has_image)
        self.assertFalse(self.panel.preview_button.isEnabled())

    def test_main_window_selection_and_removal_remain_synchronized(self):
        window = MainWindow()
        try:
            window.append_files(self.files)
            wait_for(self.app, lambda: window.validation_counts[None] == 0)
            wait_for(self.app, lambda: not window.preview.jobs)
            window.file_list.setCurrentRow(1)
            self.assertEqual(window.preview.current_file, self.files[1])
            window.preview.move(-1)
            self.assertEqual(window.file_list.currentRow(), 0)
            window.remove_selected_images()
            self.assertEqual(window.files, [self.files[1]])
            self.assertEqual(window.preview.current_file, self.files[1])
            window.clear_images()
            self.assertIsNone(window.preview.current_file)
        finally:
            window.preview.load_pool.waitForDone()
            self.app.processEvents()
            window.close()
            wait_for(self.app, lambda: not window.validation_worker.isRunning())

    def test_temporary_preview_uses_all_settings_and_removes_output(self):
        directories = []
        for mode in ("none", "fast", "ai"):
            settings = {**self.settings, "background_mode": mode}

            def process(file, directory, actual_settings):
                self.assertEqual(actual_settings, settings)
                directories.append(directory)
                output = get_output_path(file, directory, mode)
                image = QImage(320, 160, QImage.Format.Format_ARGB32)
                image.fill(QColor("#80aa44bb"))
                image.save(str(output))
                return {"success": True, "output": str(output)}

            with patch.object(WorkerManager, "process_image", side_effect=process):
                result = process_preview(self.files[0], settings)
            self.assertEqual((result.width(), result.height()), (320, 160))
            self.assertFalse(Path(directories[-1]).exists())
            self.assertEqual(len(list(Path(self.directory.name).iterdir())), 2)


if __name__ == "__main__":
    unittest.main()
