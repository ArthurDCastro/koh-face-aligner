# Portable PyInstaller specification; run through scripts/build.py.
import sys
from pathlib import Path

root = Path(SPECPATH).parent
sys.path.insert(0, str(root))
from src.version import BUNDLE_IDENTIFIER, VERSION, build_identity
from scripts.build import macos_info_plist

identity = build_identity()
name = identity['artifact']
windows = sys.platform == 'win32'
macos = sys.platform == 'darwin'
icon_dir = root / 'assets' / 'icons'
icon = str(icon_dir / ('koh.ico' if windows else 'koh.png'))

a = Analysis(
    [str(root / 'src' / 'main.py')],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / 'models'), 'models'), (str(icon_dir), 'assets/icons'),
           (str(root / 'build' / 'build-info.json'), '.')],
    hiddenimports=['src.worker', 'src.validation'],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, *([a.binaries, a.datas] if windows else []),
    exclude_binaries=not windows,
    name=name, console=not macos,
    # Retain inherited CLI output, hide the console on Windows double-click launches.
    hide_console='hide-early' if windows else None,
    icon=icon,
    version=str(root / 'build' / 'windows-version.txt') if windows else None,
)
if not windows:
    coll = COLLECT(exe, a.binaries, a.datas, name=name)
if macos:
    app = BUNDLE(
        coll, name=f'{name}.app', icon=icon,
        bundle_identifier=BUNDLE_IDENTIFIER, version=VERSION,
        info_plist=macos_info_plist(),
    )
