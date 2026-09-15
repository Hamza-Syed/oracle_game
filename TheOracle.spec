# Build with: .venv\Scripts\python.exe -m PyInstaller --noconfirm TheOracle.spec
# One-folder GUI build; no developer saves, tests, or screenshots are bundled.
from pathlib import Path

project = Path(SPECPATH)
a = Analysis(
    [str(project / 'gui.py')],
    pathex=[str(project)],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'unittest'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='TheOracle',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='TheOracle')
