"""Content validation, cloud placeholders, validator isolation and GUI filtering."""
import errno
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import threading
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import cv2
from PIL import Image
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from src.image_io import load_image
from src.interface import MainWindow
from src.validation import check_metadata, error_record, validate_image, ValidationError
from src.validation_worker import ValidationSession
from tests.test_preview import wait_for


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.valid = self.root / "portrait.png"
        Image.new("RGB", (32, 24), "purple").save(self.valid)

    def test_content_is_validated_instead_of_extension_and_decoded_once(self):
        renamed = self.root / "portrait.txt"
        renamed.write_bytes(self.valid.read_bytes())
        with patch("cv2.imdecode", wraps=cv2.imdecode) as decode:
            result = validate_image(renamed)
        self.assertTrue(result["valid"])
        self.assertEqual(result["format"], "PNG")
        self.assertEqual(result["width"], 32)
        self.assertEqual(decode.call_count, 1)
        renamed.write_text("This is not an image", encoding="utf-8")
        self.assertEqual(validate_image(renamed)["category"], "invalid_image")

    def test_missing_nonregular_empty_unsupported_and_corrupted_files(self):
        empty = self.root / "empty.jpg"
        empty.touch()
        gif = self.root / "disguised.png"
        Image.new("RGB", (2, 2)).save(gif, format="GIF")
        corrupt = self.root / "corrupt.png"
        corrupt.write_bytes(self.valid.read_bytes()[:50])
        for path, category in ((self.root / "missing.jpg", "missing_file"),
                               (self.root, "not_regular_file"), (empty, "empty_file"),
                               (gif, "unsupported_format"), (corrupt, "invalid_image")):
            with self.subTest(category=category):
                result = validate_image(path)
                self.assertFalse(result["valid"])
                self.assertEqual(result["category"], category)
                self.assertEqual(result["path"], str(path))
                self.assertEqual(result["filename"], path.name)
                self.assertTrue(result["details"])

    def test_actual_read_permission_errors_and_decode_failures_are_distinct(self):
        with patch("src.validation.os.open", side_effect=PermissionError(errno.EACCES, "Denied")):
            result = validate_image(self.valid)
        self.assertEqual(result["category"], "permission_denied")
        with patch("cv2.imdecode", return_value=None):
            self.assertEqual(validate_image(self.valid)["category"], "decode_failed")
        with patch("cv2.imdecode", side_effect=RuntimeError("decoder malfunction")):
            result = validate_image(self.valid)
        self.assertEqual(result["category"], "unexpected_error")
        self.assertIn("decoder malfunction", result["details"])

    def test_cloud_flags_and_icloud_stubs_are_identified_without_reading(self):
        metadata = dict(st_mode=0o100644, st_size=100)
        for extra in ({"st_file_attributes": 0x1000}, {"st_file_attributes": 0x40000},
                      {"st_file_attributes": 0x400000}, {"st_flags": 0x40000000}):
            with self.subTest(flags=extra), self.assertRaises(ValidationError) as error:
                check_metadata(self.valid, SimpleNamespace(**metadata, **extra))
            self.assertEqual(error.exception.category, "cloud_unavailable")
            self.assertIn("offline", str(error.exception))
        with self.assertRaises(ValidationError):
            check_metadata(self.root / ".portrait.png.icloud", SimpleNamespace(**metadata))
        # An ordinary reparse point, sparse file or unpinned-but-cached file is valid.
        check_metadata(self.valid, SimpleNamespace(**metadata, st_file_attributes=0x100600))
        cloud_folder = self.root / "OneDrive"
        cloud_folder.mkdir()
        local = cloud_folder / "available.png"
        local.write_bytes(self.valid.read_bytes())
        self.assertTrue(validate_image(local)["valid"])
        error = OSError("Provider error in any system language")
        error.winerror = 362
        self.assertEqual(error_record(local, error)["category"], "cloud_unavailable")

    def test_truncated_jpeg_is_rejected_even_if_decoder_would_tolerate_it(self):
        path = self.root / "truncated.jpg"
        Image.new("RGB", (32, 24), "purple").save(path)
        path.write_bytes(path.read_bytes()[:-2])
        result = validate_image(path)
        self.assertFalse(result["valid"])
        self.assertEqual(result["category"], "invalid_image")

    def test_processing_rechecks_files_that_change_after_validation(self):
        self.assertTrue(validate_image(self.valid)["valid"])
        self.valid.unlink()
        with self.assertRaises(FileNotFoundError):
            load_image(self.valid)
        self.valid.touch()
        with self.assertRaises(ValidationError) as error:
            load_image(self.valid)
        self.assertEqual(error.exception.category, "empty_file")

    def test_subprocess_reuse_timeout_recovery_and_folder_errors(self):
        session = ValidationSession()
        self.addCleanup(session.close)
        self.assertTrue(session.request(str(self.valid))["valid"])
        pid = session.process.pid
        self.assertTrue(session.request(str(self.valid))["valid"])
        self.assertEqual(session.process.pid, pid)
        folder = session.request(str(self.root), "folder")
        self.assertIn(str(self.valid), folder["files"])
        missing = session.request(str(self.root / "missing"), "folder")
        self.assertEqual(missing["category"], "missing_file")
        session.stop_process()
        session.timeout = 0
        timed_out = session.request(str(self.valid))
        self.assertEqual(timed_out["category"], "validation_timeout")
        self.assertIsNone(session.process)
        session.timeout = 15
        self.assertTrue(session.request(str(self.valid))["valid"])


class ValidationGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.valid = self.root / "valid.png"
        Image.new("RGB", (32, 24), "purple").save(self.valid)
        self.invalid = self.root / "bad.jpg"
        self.invalid.write_bytes(b"not an image")
        self.window = MainWindow()

    def tearDown(self):
        self.window.progress_timer.stop()
        self.window.preview.batch_active = False
        self.window.batch_active = False
        self.window.close()
        wait_for(self.app, lambda: not self.window.validation_worker.isRunning())
        self.window.preview.load_pool.waitForDone()
        self.app.processEvents()
        self.directory.cleanup()

    def wait_validation(self):
        wait_for(self.app, lambda: self.window.validation_counts[None] == 0)

    def test_counts_invalid_reasons_retry_removal_and_batch_filter(self):
        self.window.append_files([str(self.valid), str(self.invalid), str(self.valid)])
        self.wait_validation()
        self.assertEqual(len(self.window.files), 2)
        self.assertEqual(self.window.validation_label.text(), "Valid: 1 | Invalid: 1 | Checking: 0")
        self.assertIn("recognized image", self.window.file_list.item(1).text())
        self.assertIn("Category: invalid_image", self.window.file_list.item(1).toolTip())
        self.window.file_list.setCurrentRow(1)
        self.assertFalse(self.window.preview.preview_button.isEnabled())
        self.assertFalse(self.window.preview.original.has_image)
        self.assertTrue(self.window.process_button.isEnabled())
        self.window.output_dir = self.directory.name
        with patch("src.interface.ProcessingWorker") as worker:
            self.window.start_processing()
            self.assertEqual(worker.call_args.kwargs["files"], [str(self.valid)])
            self.window.worker = None
        self.window.preview.end_batch()
        self.window.reset_controls()
        self.invalid.write_bytes(self.valid.read_bytes())
        self.window.retry_validation()
        self.wait_validation()
        self.assertEqual(self.window.validation_counts[True], 2)
        self.invalid.write_bytes(b"broken again")
        self.window.retry_validation()
        self.wait_validation()
        self.window.remove_invalid_images()
        self.assertEqual(self.window.files, [str(self.valid)])
        self.assertEqual(self.window.validation_label.text(), "Valid: 1 | Invalid: 0 | Checking: 0")

    def test_gui_remains_responsive_and_removed_results_are_ignored(self):
        started, release = threading.Event(), threading.Event()
        real_request = ValidationSession.request

        def request(session, file, action="image", interrupted=lambda: False):
            started.set()
            release.wait(3)
            return real_request(session, file, action, interrupted)

        with patch.object(ValidationSession, "request", request):
            try:
                self.window.append_files([str(self.valid)])
                wait_for(self.app, started.is_set)
                self.assertFalse(self.window.process_button.isEnabled())
                self.assertFalse(self.window.preview.preview_button.isEnabled())
                ticks = []
                QTimer.singleShot(0, lambda: ticks.append(True))
                wait_for(self.app, lambda: bool(ticks))
                old_token = self.window.validation_tokens[str(self.valid)]
                self.window.clear_images()
                self.window.append_files([str(self.valid)])
                self.window.validation_finished(str(self.valid), old_token, {"valid": False, "error": "old result"})
                self.assertIsNone(self.window.validation_results[str(self.valid)]["valid"])
            finally:
                release.set()
            self.wait_validation()
        self.assertEqual(self.window.validation_counts[True], 1)
        self.assertEqual(self.window.validation_counts[False], 0)

    def test_valid_files_can_start_while_other_validation_is_pending(self):
        with patch.object(self.window.validation_worker, "submit"):
            self.window.append_files([str(self.valid), str(self.invalid)])
        token = self.window.validation_tokens[str(self.valid)]
        self.window.validation_finished(str(self.valid), token, validate_image(self.valid))
        self.assertEqual(self.window.validation_counts[None], 1)
        self.assertTrue(self.window.process_button.isEnabled())
        self.window.output_dir = self.directory.name
        with patch("src.interface.ProcessingWorker") as worker:
            self.window.start_processing()
            self.assertEqual(worker.call_args.kwargs["files"], [str(self.valid)])
            self.window.worker = None

    def test_all_invalid_files_cannot_start_processing(self):
        self.window.append_files([str(self.invalid)])
        self.wait_validation()
        self.assertFalse(self.window.process_button.isEnabled())
        self.window.output_dir = self.directory.name
        with patch("src.interface.ProcessingWorker") as worker:
            self.window.start_processing()
            worker.assert_not_called()

    def test_folder_import_is_asynchronous_and_cloud_stubs_are_reported(self):
        stub = self.root / ".offline.jpg.icloud"
        stub.write_bytes(b"placeholder metadata")
        with patch("src.interface.QFileDialog.getExistingDirectory", return_value=str(self.root)):
            self.window.add_folder()
        self.assertIn(str(self.root), self.window.folder_tokens)
        wait_for(self.app, lambda: not self.window.folder_tokens)
        self.wait_validation()
        self.assertEqual(self.window.validation_counts[True], 1)
        self.assertEqual(self.window.validation_counts[False], 2)
        self.assertEqual(self.window.validation_results[str(stub)]["category"], "cloud_unavailable")

    def test_processing_availability_failure_updates_validation_feedback(self):
        self.window.append_files([str(self.valid)])
        self.wait_validation()
        failure = error_record(self.valid, FileNotFoundError("File disappeared"))
        self.window.image_finished({**failure, "success": False})
        self.assertEqual(self.window.validation_counts[False], 1)
        self.assertIn("File not found", self.window.file_list.item(0).text())


if __name__ == "__main__":
    unittest.main()
