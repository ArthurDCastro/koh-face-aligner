"""Progress tests run without models or real image processing."""
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from src.interface import MainWindow, ProcessingWorker
from src.worker_manager import WorkerManager


class BatchProgressTests(unittest.TestCase):
    def test_all_modes_count_failures_and_announce_current_file(self):
        for mode in ("none", "fast", "ai"):
            with self.subTest(mode=mode):
                events = []
                reported_errors = []
                reported_results = []
                manager = WorkerManager()

                def process(file, output, settings):
                    self.assertEqual(settings["background_mode"], mode)
                    events.append(("process", file))
                    if file == "exception.jpg":
                        raise RuntimeError("broken image")
                    return {"success": file == "ok.jpg", "file": file, "error": "timeout"}

                with patch.object(manager, "process_image", side_effect=process):
                    results = manager.process_batch(
                        ["ok.jpg", "failed.jpg", "exception.jpg"], "output",
                        {"background_mode": mode},
                        callback=lambda current, total: events.append((current, total)),
                        started_callback=lambda file: events.append(("start", file)),
                        error_callback=reported_errors.append,
                        result_callback=reported_results.append,
                    )
                self.assertEqual(results["success"], 1)
                self.assertEqual(len(results["errors"]), 2)
                self.assertEqual(reported_errors, results["errors"])
                self.assertEqual([result["success"] for result in reported_results], [True, False, False])
                self.assertEqual(reported_results[-1]["error"], "broken image")
                self.assertEqual(events, [
                    ("start", "ok.jpg"), ("process", "ok.jpg"), (1, 3),
                    ("start", "failed.jpg"), ("process", "failed.jpg"), (2, 3),
                    ("start", "exception.jpg"), ("process", "exception.jpg"), (3, 3),
                ])


class GuiProgressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = MainWindow()
        self.window.files = [f"{i}.jpg" for i in range(15)]
        for file in self.window.files:
            self.window.set_validation_result(file, {"valid": True})
        self.window.output_dir = "output"
        self.clock = patch("src.interface.time.monotonic", return_value=100)
        self.now = self.clock.start()
        self.worker_patch = patch("src.interface.ProcessingWorker")
        self.worker_class = self.worker_patch.start()
        self.worker_class.return_value.isRunning.return_value = False
        self.window.start_processing()

    def tearDown(self):
        self.window.progress_timer.stop()
        self.window.close()
        self.worker_patch.stop()
        self.clock.stop()

    def test_live_timer_eta_and_moving_window(self):
        self.assertTrue(self.window.progress_timer.isActive())
        self.assertEqual(self.window.count_label.text(), "Processed: 0 / 15")
        self.window.update_filename("/images/current.jpg")
        self.assertEqual(self.window.filename_label.text(), "Current image: current.jpg")
        self.now.return_value = 110
        self.window.update_progress(1, 15, 10)
        self.assertIn("Calculating...", self.window.time_label.text())
        self.now.return_value = 120
        self.window.update_progress(2, 15, 10)
        self.assertIn("Remaining: 00:02:10", self.window.time_label.text())
        self.window.update_filename("next.jpg")
        self.now.return_value = 125
        # The same signal used by the once-per-second timer updates during an image.
        self.window.progress_timer.timeout.emit()
        self.assertIn("Elapsed: 00:00:25", self.window.time_label.text())
        self.assertIn("Remaining: 00:02:05", self.window.time_label.text())
        for current in range(3, 14):
            self.window.update_progress(current, 15, 2)
        self.assertEqual(list(self.window.image_durations), [2] * 10)

    def test_worker_reports_filename_and_per_image_duration(self):
        worker = ProcessingWorker([], "output", {})
        filenames = []
        progress = []
        worker.image_started.connect(filenames.append)
        worker.progress.connect(lambda *values: progress.append(values))
        worker.report_started("portrait.jpg")
        self.now.return_value = 104
        worker.report_progress(1, 2)
        self.assertEqual(filenames, ["portrait.jpg"])
        self.assertEqual(progress, [(1, 2, 4.0)])
        results = []
        worker.image_finished.connect(results.append)
        worker.settings = {"width": 400, "background_mode": "ai"}
        worker.report_result({"success": True, "file": "portrait.jpg", "output": "koh_portrait.png"})
        worker.settings["width"] = 800
        self.assertEqual(results[0]["settings"]["width"], 400)
        self.assertEqual(results[0]["output"], "koh_portrait.png")

    def test_error_list_counts_failures_and_resets_for_next_batch(self):
        self.window.add_image_error({"file": "/images/broken.jpg", "error": "No face detected"})
        self.window.add_image_error({"file": "/images/slow.jpg", "error": "Processing timeout"})
        self.assertEqual(self.window.error_count_label.text(), "Images with errors: 2")
        self.assertEqual(self.window.error_list.item(0).text(), "broken.jpg: No face detected")
        self.assertIn("/images/broken.jpg", self.window.error_list.item(0).toolTip())
        with patch("src.interface.QMessageBox.critical"):
            self.window.processing_failed("batch failed")
        self.assertEqual(self.window.error_list.count(), 2)
        self.window.start_processing()
        self.assertEqual(self.window.error_list.count(), 0)
        self.assertEqual(self.window.error_count_label.text(), "Images with errors: 0")

    def test_progress_colors_follow_batch_errors_and_reset(self):
        self.assertEqual(self.window.progress_bar.styleSheet(), "")
        for index in range(15):
            self.window.add_image_error({"file": f"{index}.jpg", "error": "No face"})
            color = "#C96379" if index == 14 else "#D6A34A"
            self.assertIn(color, self.window.progress_bar.styleSheet())
        self.assertEqual(self.window.progress_bar.toolTip(), "All images failed")
        self.window.start_processing()
        self.assertEqual(self.window.progress_bar.styleSheet(), "")
        self.assertEqual(self.window.progress_bar.toolTip(), "")
        self.window.update_progress_color(errors=1, total=15)
        self.assertIn("#D6A34A", self.window.progress_bar.styleSheet())
        self.window.update_progress_color(errors=0, total=15)
        self.assertEqual(self.window.progress_bar.styleSheet(), "")

    def test_completion_freezes_duration_and_next_batch_resets(self):
        self.now.return_value = 145
        self.window.update_progress(15, 15, 3)
        with patch("src.interface.QMessageBox.information") as message:
            self.window.processing_completed({"total": 15, "success": 15, "errors": []})
        self.assertFalse(self.window.progress_timer.isActive())
        self.assertEqual(self.window.progress_bar.value(), 100)
        self.assertEqual(self.window.time_label.text(), "Duration: 00:00:45")
        self.assertIn("Duration: 00:00:45", message.call_args.args[2])
        self.now.return_value = 200
        self.window.start_processing()
        self.assertEqual(self.window.completed_images, 0)
        self.assertEqual(len(self.window.image_durations), 0)
        self.assertEqual(self.window.progress_bar.value(), 0)
        self.assertIn("Elapsed: 00:00:00", self.window.time_label.text())

    def test_batch_failure_stops_timer_and_preserves_partial_count(self):
        self.window.update_progress(1, 15, 2)
        self.now.return_value = 107
        with patch("src.interface.QMessageBox.critical"):
            self.window.processing_failed("worker unavailable")
        self.assertFalse(self.window.progress_timer.isActive())
        self.assertEqual(self.window.count_label.text(), "Processed: 1 / 15")
        self.assertIn("#C96379", self.window.progress_bar.styleSheet())
        self.assertIn("Duration: 00:00:07", self.window.time_label.text())
        self.assertTrue(self.window.process_button.isEnabled())


if __name__ == "__main__":
    unittest.main()
