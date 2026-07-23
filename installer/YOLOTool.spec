# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

SPEC_ROOT = Path(SPECPATH).resolve()
ROOT = SPEC_ROOT.parent
HOOKS_DIR = ROOT / "installer" / "hooks"
ASSETS_DIR = ROOT / "src" / "assets"

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

BASE_EXCLUDES = [
    "pytest",
    "src.tests",
    "PySide6.scripts.deploy_lib",
    "torch.utils.tensorboard",
    "tensorboard",
    "dask",
    "matplotlib.tests",
    # Optional data/audio and test-only packages are not used by YOLOTool.
    "polars",
    "_polars_runtime_32",
    "torchaudio",
    "torch.fx.passes.tests",
    "torch._export.db.examples",
    "torch.utils.benchmark",
    "torch.distributed.rpc._testing",
    "torch.distributed.rpc.examples",
    "torch._numpy.testing",
]

mode = os.environ.get("YOLO_TOOL_BUILD_MODE", "release").strip().lower()
is_dev = mode == "dev"
name = "YOLOTool-dev" if is_dev else "YOLOTool"

datas = [*collect_data_files("ultralytics")]
binaries = []
for package in ("torch", "cv2"):
    binaries += collect_dynamic_libs(package)

hiddenimports = collect_submodules("ultralytics", on_error="ignore")
if not is_dev:
    datas += collect_data_files(
        "matplotlib",
        subdir="mpl-data",
        excludes=["**/sample_data/**"],
    )
    hiddenimports += [
        "matplotlib",
        "matplotlib.backends.backend_agg",
        "matplotlib.backends.backend_qtagg",
    ]

excludes = list(BASE_EXCLUDES)

a = Analysis(
    [str(ROOT / "src/main.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[str(HOOKS_DIR)],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=name,
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
    icon=str(ASSETS_DIR / "app_icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=name,
)

