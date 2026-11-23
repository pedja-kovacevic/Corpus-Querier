# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hiddenimports = collect_submodules("customtkinter")
# Pillow imports this helper dynamically when ImageTk initializes its Tcl
# command. PyInstaller cannot discover that import statically, which caused
# the Linux build to crash before the launcher window appeared.
hiddenimports += ["PIL._tkinter_finder"]
datas = collect_data_files("customtkinter")
datas += [("assets/corpus-querier.png", "assets")]
datas += [("assets/linux-icons/64x64/corpus-querier-data-bird.png", "assets")]

icon_file = str(
    Path("assets")
    / ("corpus-querier.ico" if sys.platform == "win32" else "corpus-querier.png")
)

a = Analysis(
    ["Corpus-Querier.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Corpus Querier",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
)

if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="Corpus Querier.app",
        bundle_identifier="io.github.pedjakovacevic.corpusquerier",
        icon="assets/corpus-querier.png",
        info_plist={
            "CFBundleDisplayName": "Corpus Querier",
            "CFBundleShortVersionString": "3.1.4",
            "CFBundleVersion": "3.1.4",
            "NSHighResolutionCapable": True,
        },
    )
