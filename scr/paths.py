from __future__ import annotations

import sys
from pathlib import Path


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


ROOT = app_root()
PACKAGE_ROOT = Path(__file__).resolve().parent
ASSETS_ROOT = PACKAGE_ROOT / "assets"
DATA_ROOT = ROOT / "data"
RUNTIME_ROOT = DATA_ROOT / "runtime"
DEFAULT_SETTINGS_PATH = RUNTIME_ROOT / "settings.json"
ICON_PNG = ASSETS_ROOT / "app_icon.png"
ICON_ICO = ASSETS_ROOT / "app_icon.ico"
