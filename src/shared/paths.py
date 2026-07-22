from __future__ import annotations

import sys
from pathlib import Path


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def resource_root() -> Path:
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass).resolve()
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


ROOT = app_root()
PACKAGE_ROOT = resource_root() / "src"
ASSETS_ROOT = PACKAGE_ROOT / "assets"
DATA_ROOT = ROOT / "data"
RUNTIME_ROOT = DATA_ROOT / "runtime"
DEFAULT_SETTINGS_PATH = RUNTIME_ROOT / "settings.json"
ICON_PNG = ASSETS_ROOT / "app_icon.png"
ICON_ICO = ASSETS_ROOT / "app_icon.ico"
