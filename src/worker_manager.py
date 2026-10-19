
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import psutil


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class WorkerManager:
    """Run image processing in isolated subprocesses."""

    def __init__(
        self,
        max_memory_mb=4096,
        max_time_seconds=120,
        check_interval=0.2,
    ):
        self.max_memory_mb = max_memory_mb
        self.max_time_seconds = max_time_seconds
        self.check_interval = check_interval

    @staticmethod
    def get_memory_mb(process):
        """Get RSS memory used by a process and its children."""
        try:
            processes = [process] + process.children(recursive=True)

            return sum(
                child.memory_info().rss
                for child in processes
                if child.is_running()
            ) / (1024 ** 2)

        except psutil.Error:
            return 0.0

    @staticmethod
    def stop_process(process):
        """Terminate a process and its child processes."""
        try:
            children = process.children(recursive=True)

            for child in children:
                try:
                    child.terminate()
                except psutil.Error:
                    pass

            process.terminate()

            _, alive = psutil.wait_procs(
                children + [process],
                timeout=2,
            )

            for child in alive:
                try:
                    child.kill()
                except psutil.Error:
                    pass

        except psutil.Error:
            pass

    def process_image(self, file, output_dir, settings):
        """Process one image and return its result."""
        file = Path(file)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(
            prefix="koh_worker_"
        ) as temporary_dir:
            report_path = Path(temporary_dir) / "report.json"
            log_path = Path(temporary_dir) / "worker.log"

            
            # Use the bundled executable when running with PyInstaller
            if getattr(sys, "frozen", False):
                command = [
                    sys.executable,
                    "--koh-worker",
                ]
            else:
                command = [
                    sys.executable,
                    "-m",
                    "src.worker",
                ]

            command.extend([
                "--input", str(file.resolve()),
                "--output", str(output_dir.resolve()),
                "--report", str(report_path),
                "--width", str(settings["width"]),
                "--height", str(settings["height"]),
                "--face-ratio", str(settings["face_ratio"]),
                "--position-x", str(settings["position_x"]),
                "--position-y", str(settings["position_y"]),
                "--background-mode", settings["background_mode"],
            ])


            creationflags = (
                subprocess.CREATE_NO_WINDOW
                if os.name == "nt"
                else 0
            )

            start = time.monotonic()
            peak_memory = 0.0
            failure = None

            with log_path.open("w", encoding="utf-8") as log:
                worker = subprocess.Popen(
                    command,
                    cwd=PROJECT_ROOT,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    creationflags=creationflags,
                )

                process = psutil.Process(worker.pid)

                while worker.poll() is None:
                    memory = self.get_memory_mb(process)
                    peak_memory = max(peak_memory, memory)

                    elapsed = time.monotonic() - start

                    if memory > self.max_memory_mb:
                        failure = "Memory limit exceeded"
                        self.stop_process(process)
                        break

                    if elapsed > self.max_time_seconds:
                        failure = "Processing timeout"
                        self.stop_process(process)
                        break

                    time.sleep(self.check_interval)

                try:
                    worker.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.stop_process(process)
                    worker.kill()
                    worker.wait()

            elapsed = time.monotonic() - start

            if failure:
                return {
                    "success": False,
                    "file": str(file),
                    "error": failure,
                    "time": elapsed,
                    "peak_memory_mb": peak_memory,
                }

            if report_path.exists():
                try:
                    report = json.loads(
                        report_path.read_text(encoding="utf-8")
                    )

                    success = report.get("success", 0) == 1

                    errors = report.get("errors", [])
                    error_message = (
                        errors[0].get("error", "Processing failed")
                        if errors
                        else report.get("error", "Processing failed")
                    )

                    if worker.returncode != 0:
                        success = False

                    return {
                        "success": success,
                        "file": str(file),
                        "error": None if success else error_message,
                        "time": elapsed,
                        "peak_memory_mb": peak_memory,
                    }

                except (OSError, ValueError, TypeError, KeyError):
                    pass

            log_text = log_path.read_text(
                encoding="utf-8",
                errors="replace",
            )

            return {
                "success": False,
                "file": str(file),
                "error": (
                    log_text[-1000:]
                    or f"Worker exited with code {worker.returncode}"
                ),
                "time": elapsed,
                "peak_memory_mb": peak_memory,
            }

    def process_batch(
        self,
        files,
        output_dir,
        settings,
        callback=None,
    ):
        """Process a batch sequentially with resource monitoring."""
        results = {
            "total": len(files),
            "success": 0,
            "errors": [],
        }

        for index, file in enumerate(files, start=1):
            try:
                result = self.process_image(
                    file,
                    output_dir,
                    settings,
                )

                if result["success"]:
                    results["success"] += 1
                else:
                    results["errors"].append({
                        "file": result["file"],
                        "error": result["error"],
                    })

            except Exception as error:
                results["errors"].append({
                    "file": str(file),
                    "error": str(error),
                })

            if callback:
                callback(index, len(files))

        return results
