from __future__ import annotations

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules


ROOT = Path(__file__).resolve().parent.parent
HOOKS_DIR = ROOT / "installer" / "hooks"
ASSETS_DIR = ROOT / "scr" / "assets"
MODELS_DIR = ROOT / "data" / "models"
ROOT_MODEL_FILES = [
    ROOT / "yolo26n.pt",
]

BASE_EXCLUDES = [
    "pytest",
    "scr.tests",
    "PySide6.scripts.deploy_lib",
    "torch.utils.tensorboard",
    "tensorboard",
    "dask",
    "matplotlib.tests",
]

DEV_EXCLUDES = [
    "torchaudio",
]


def build_packaging(mode: str) -> dict[str, object]:
    is_dev = mode == "dev"
    name = "YOLOTool-dev" if is_dev else "YOLOTool"
    datas = [
        (str(ASSETS_DIR), "scr/assets"),
        *collect_data_files("ultralytics"),
    ]
    if MODELS_DIR.exists():
        for model_path in sorted(MODELS_DIR.glob("*.pt")):
            if model_path.is_file():
                datas.append((str(model_path), "data/models"))
    for model_path in ROOT_MODEL_FILES:
        if model_path.exists():
            datas.append((str(model_path), "."))
    binaries = []
    for package in ("torch", "cv2"):
        binaries += collect_dynamic_libs(package)

    hiddenimports = collect_submodules("ultralytics")
    if not is_dev:
        datas += collect_data_files("matplotlib", subdir="mpl-data")
        hiddenimports += [
            "matplotlib",
            "matplotlib.backends.backend_agg",
            "matplotlib.backends.backend_qtagg",
        ]

    excludes = list(BASE_EXCLUDES)
    if is_dev:
        excludes += DEV_EXCLUDES

    return {
        "name": name,
        "datas": datas,
        "binaries": binaries,
        "hiddenimports": hiddenimports,
        "excludes": excludes,
        "hookspath": [str(HOOKS_DIR)],
        "icon": str(ASSETS_DIR / "app_icon.ico"),
    }
