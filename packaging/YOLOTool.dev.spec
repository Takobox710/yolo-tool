# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

SPEC_ROOT = Path(SPECPATH).resolve()
sys.path.insert(0, str(SPEC_ROOT))

from pyinstaller_common import ROOT, build_packaging


config = build_packaging("dev")

a = Analysis(
    [str(ROOT / "scr/main.py")],
    pathex=[str(ROOT)],
    binaries=config["binaries"],
    datas=config["datas"],
    hiddenimports=config["hiddenimports"],
    hookspath=config["hookspath"],
    hooksconfig={},
    runtime_hooks=[],
    excludes=config["excludes"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=config["name"],
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=config["icon"],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=config["name"],
)
