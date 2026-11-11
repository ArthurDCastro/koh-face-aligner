"""Background validation with a reusable, resource-limited subprocess."""
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import time

import psutil
from PySide6.QtCore import QThread, Signal

from src.validation import ValidationError, error_record
from src.worker_manager import PROJECT_ROOT, WorkerManager


class ValidationSession:
    def __init__(self, timeout=15, memory_mb=1024):
        self.timeout = timeout
        self.memory_mb = memory_mb
        self.directory = tempfile.TemporaryDirectory(prefix="koh_validation_")
        self.process = None
        self.log = None

    def stop_process(self):
        if self.process is not None:
            if self.process.poll() is None:
                try:
                    WorkerManager.stop_process(psutil.Process(self.process.pid))
                except psutil.Error:
                    pass
                if self.process.poll() is None:
                    self.process.kill()
            self.process.wait()
            self.process = None
        if self.log is not None:
            self.log.close()
            self.log = None

    def close(self):
        self.stop_process()
        self.directory.cleanup()

    def request(self, file, action="image", interrupted=lambda: False):
        try:
            report = Path(self.directory.name) / "report.json"
            report.unlink(missing_ok=True)
            request_path = Path(self.directory.name) / "request.json"
            request_path.unlink(missing_ok=True)
            if self.process is None or self.process.poll() is not None:
                self.stop_process()
                command = ([sys.executable, "--koh-validator"] if getattr(sys, "frozen", False)
                           else [sys.executable, "-m", "src.validation"])
                command.extend(["--requests", self.directory.name])
                self.log = (Path(self.directory.name) / "validation.log").open("w", encoding="utf-8")
                self.process = subprocess.Popen(
                    command, cwd=PROJECT_ROOT, stdin=subprocess.DEVNULL,
                    stdout=self.log, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
            # File-based IPC also works in --windowed builds with no sys.stdin.
            temporary = request_path.with_suffix(".tmp")
            temporary.write_text(json.dumps({"file": file, "action": action, "report": str(report)}), encoding="utf-8")
            temporary.replace(request_path)
            start = time.monotonic()
            monitor = psutil.Process(self.process.pid)
            while not report.is_file():
                if interrupted():
                    return None
                if time.monotonic() - start > self.timeout:
                    raise ValidationError("validation_timeout", "Validation timed out. If this is a cloud or network file, download it or make it available offline and retry.",
                                          f"Read/decode exceeded {self.timeout} seconds")
                if WorkerManager.get_memory_mb(monitor) > self.memory_mb:
                    raise ValidationError("validation_resource_limit", "Image validation exceeded the memory limit.", f"Validator exceeded {self.memory_mb} MB")
                if self.process.poll() is not None:
                    log = Path(self.log.name).read_text(encoding="utf-8", errors="replace")
                    raise ValidationError("validation_failed", "Image validator stopped unexpectedly. Retry validation.", log[-2000:])
                time.sleep(0.05)
            return json.loads(report.read_text(encoding="utf-8"))
        except Exception as error:
            self.stop_process()
            return error_record(file, error)


class ValidationWorker(QThread):
    validated = Signal(str, int, dict)
    folder_loaded = Signal(str, int, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.queue = queue.Queue()
        self.latest = {}
        self.lock = threading.Lock()

    def submit(self, file, token, action="image"):
        with self.lock:
            self.latest[(action, file)] = token
        self.queue.put((file, token, action))
        if not self.isRunning():
            self.start()

    def cancel(self, file, action="image"):
        with self.lock:
            self.latest.pop((action, file), None)

    def run(self):
        session = None
        try:
            while not self.isInterruptionRequested():
                try:
                    file, token, action = self.queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                with self.lock:
                    if self.latest.get((action, file)) != token:
                        continue
                try:
                    if session is None:
                        session = ValidationSession()
                    result = session.request(file, action, self.isInterruptionRequested)
                except Exception as error:
                    result = error_record(file, error)
                if result is not None:
                    signal = self.folder_loaded if action == "folder" else self.validated
                    signal.emit(file, token, result)
        finally:
            if session is not None:
                session.close()
