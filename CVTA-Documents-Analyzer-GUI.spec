# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import PySide6


project_root = Path(SPECPATH)
pyside_dir = Path(PySide6.__file__).resolve().parent

a = Analysis(
    ["src/luncher.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(project_root / "src" / "ui" / "qml"), "ui/qml"),
        (str(project_root / "src" / "config" / "prompts.json"), "src/config"),
        (str(pyside_dir / "qml"), "PySide6/qml"),
    ],
    hiddenimports=[
        "PySide6.QtOpenGL",
        "PySide6.QtQuick",
        "PySide6.QtQuickControls2",
        "PySide6.QtSvg",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PySide6.QtWebEngine",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CVTA-Documents-Analyzer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="CVTA-Documents-Analyzer",
)
