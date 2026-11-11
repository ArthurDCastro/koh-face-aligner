"""Version, metadata, packaging and tag consistency tests without native compilers."""
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from scripts import build
from src import __version__
from src.interface import MainWindow
from src.version import APP_NAME, BUNDLE_IDENTIFIER, VERSION, VERSION_PARTS, build_identity, check_tag, version_parts


class VersionTests(unittest.TestCase):
    def test_semver_and_tag_validation(self):
        self.assertEqual(__version__, VERSION)
        self.assertEqual(version_parts(), VERSION_PARTS)
        self.assertEqual(len(VERSION_PARTS), 3)
        for invalid in ("1.2", "v1.2.3", "01.2.3", "1.02.3", "1.2.03", "1.2.3-beta", "1.2.3+build", "1.2.3\n"):
            with self.subTest(version=invalid), self.assertRaises(ValueError):
                version_parts(invalid)
        check_tag("")
        check_tag(f"v{VERSION}")
        with self.assertRaises(ValueError):
            check_tag("v999.0.0")

    def test_version_flags_do_not_import_gui_or_models(self):
        for flag in ("--version", "-V"):
            code = (
                "import sys; from src.main import main; "
                f"sys.argv = ['KOH', {flag!r}]; "
                "assert main() == 0; "
                "assert 'PySide6' not in sys.modules; assert 'cv2' not in sys.modules"
            )
            result = subprocess.run([sys.executable, "-c", code], cwd=build.PROJECT_ROOT,
                                    capture_output=True, text=True, check=True)
            self.assertEqual(result.stdout.strip(), f"{APP_NAME} {VERSION}")

    def test_target_names_and_architecture_detection(self):
        for system, machine, target, arch in (("win32", "AMD64", "windows", "x64"),
                                              ("linux", "x86_64", "linux", "x64"),
                                              ("darwin", "x86_64", "macos", "x64"),
                                              ("darwin", "arm64", "macos", "arm64")):
            identity = build_identity(system, machine)
            self.assertEqual(identity["artifact"], f"KOH-v{VERSION}-{target}-{arch}")
            self.assertIn(VERSION, identity["archive"])
            executable = build.executable_path(identity, Path("dist"))
            self.assertIn(identity["artifact"], executable.name)
        with self.assertRaises(ValueError):
            build_identity("win32", "x86")

    def test_ci_metadata_rejects_tag_and_target_mismatch_before_build(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "outputs"
            with redirect_stdout(StringIO()), patch.dict(os.environ, {"GITHUB_REF_TYPE": "tag", "GITHUB_REF_NAME": f"v{VERSION}"}):
                self.assertEqual(build.main(["--metadata", "--github-output", str(output)]), 0)
            self.assertIn(f"version={VERSION}\n", output.read_text())
            with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as error:
                build.main(["--metadata", "--tag", "v999.0.0"])
            self.assertEqual(error.exception.code, 2)
            with patch("scripts.build.build_identity", return_value=build_identity("linux", "x86_64")):
                with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
                    build.main(["--metadata", "--expected-architecture", "arm64"])

    def test_windows_resource_and_mac_metadata_use_central_version(self):
        # Parse the generated PyInstaller resource without Windows-only dependencies.
        def factory(*args, **kwargs):
            return SimpleNamespace(args=args, **kwargs)
        constructors = {name: factory for name in (
            "VSVersionInfo", "FixedFileInfo", "StringStruct", "StringFileInfo",
            "StringTable", "VarFileInfo", "VarStruct",
        )}
        resource = eval(build.windows_version_resource("KOH.exe"), {"__builtins__": {}}, constructors)
        self.assertEqual(resource.ffi.filevers, VERSION_PARTS + (0,))
        self.assertEqual(resource.ffi.prodvers, VERSION_PARTS + (0,))
        entries = resource.kids[0].args[0][0].args[1]
        strings = dict(entry.args for entry in entries)
        self.assertEqual(strings["ProductName"], APP_NAME)
        self.assertEqual(strings["FileVersion"], VERSION)
        self.assertEqual(strings["ProductVersion"], VERSION)
        plist = build.macos_info_plist()
        self.assertEqual(plist["CFBundleName"], APP_NAME)
        self.assertEqual(plist["CFBundleIdentifier"], BUNDLE_IDENTIFIER)
        self.assertEqual(plist["CFBundleShortVersionString"], VERSION)
        self.assertEqual(plist["CFBundleVersion"], VERSION)

    def test_spec_applies_metadata_before_native_bundle_creation(self):
        spec = (build.PROJECT_ROOT / "scripts" / "koh.spec").read_text()
        for system, machine in (("win32", "AMD64"), ("linux", "x86_64"), ("darwin", "arm64")):
            calls = {}
            def factory(name):
                def create(*args, **kwargs):
                    calls[name] = (args, kwargs)
                    return SimpleNamespace(pure=[], scripts=[], binaries=[], datas=[])
                return create
            namespace = {name: factory(name) for name in ("Analysis", "PYZ", "EXE", "COLLECT", "BUNDLE")}
            namespace["SPECPATH"] = str(build.PROJECT_ROOT / "scripts")
            with patch("sys.platform", system), patch("platform.machine", return_value=machine):
                exec(compile(spec, "koh.spec", "exec"), namespace)
            executable = calls["EXE"][1]
            self.assertEqual(executable["name"], build_identity(system, machine)["artifact"])
            if system == "win32":
                self.assertTrue(executable["console"])
                self.assertEqual(executable["hide_console"], "hide-early")
                self.assertTrue(executable["version"].endswith("windows-version.txt"))
            elif system == "darwin":
                self.assertFalse(executable["console"])
                self.assertEqual(calls["BUNDLE"][1]["info_plist"], build.macos_info_plist())

    def test_packages_contain_versioned_binaries(self):
        with tempfile.TemporaryDirectory() as directory:
            dist = Path(directory)
            for system, target in (("win32", "windows"), ("linux", "linux")):
                identity = build_identity(system, "x86_64")
                executable = build.executable_path(identity, dist)
                executable.parent.mkdir(parents=True, exist_ok=True)
                executable.write_bytes(b"test executable")
                executable.chmod(0o755)
                archive = build.package_build(identity, dist)
                self.assertIn(f"v{VERSION}-{target}-x64", archive.name)
                if target == "windows":
                    with zipfile.ZipFile(archive) as package:
                        self.assertEqual(package.namelist(), [executable.name])
                else:
                    with tarfile.open(archive) as package:
                        member = package.getmember(f"{identity['artifact']}/{executable.name}")
                        if os.name != "nt":
                            self.assertTrue(member.mode & 0o111)

    def test_about_dialog_displays_version_and_target(self):
        app = QApplication.instance() or QApplication([])
        window = MainWindow()
        try:
            with patch("src.interface.QMessageBox.about") as about:
                window.about_button.click()
            self.assertEqual(about.call_args.args[1], f"About {APP_NAME}")
            self.assertIn(VERSION, about.call_args.args[2])
            self.assertIn(build_identity()["platform"], about.call_args.args[2])
        finally:
            window.close()

    def test_gui_application_metadata_uses_version_source(self):
        from src.main import main
        app = QApplication.instance() or QApplication([])
        with patch("sys.argv", ["KOH"]), patch("PySide6.QtWidgets.QApplication") as application:
            with patch("src.interface.MainWindow"):
                application.return_value.exec.return_value = 0
                self.assertEqual(main(), 0)
        application.return_value.setApplicationName.assert_called_once_with(APP_NAME)
        application.return_value.setApplicationDisplayName.assert_called_once_with(APP_NAME)
        application.return_value.setApplicationVersion.assert_called_once_with(VERSION)


if __name__ == "__main__":
    unittest.main()
