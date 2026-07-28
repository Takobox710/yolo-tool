from __future__ import annotations

import os
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


def assets_root() -> Path:
    if getattr(sys, "frozen", False):
        return resource_root() / "src" / "assets"
    return Path(__file__).resolve().parent.parent / "assets"


ROOT = app_root()
PACKAGE_ROOT = resource_root() / "src"
ASSETS_ROOT = assets_root()
DATA_ROOT = ROOT / "data"
RUNTIME_ROOT = DATA_ROOT / "runtime"
DEFAULT_SETTINGS_PATH = RUNTIME_ROOT / "settings.json"
LOCAL_APP_DATA_ROOT = Path(
    os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
)
LEGACY_EXTENSIONS_ROOT = LOCAL_APP_DATA_ROOT / "YOLOTool" / "extensions"
INSTALL_INSTANCES_ROOT = LOCAL_APP_DATA_ROOT / "YOLOTool" / "instances"
# Compatibility alias for integrations that still inspect the legacy location.
EXTENSIONS_ROOT = LEGACY_EXTENSIONS_ROOT
ICON_PNG = ASSETS_ROOT / "app_icon.png"
ICON_ICO = ASSETS_ROOT / "app_icon.ico"
ICON_PNG_RESOURCE = ":/yolotool/app_icon.png"
ICON_ICO_RESOURCE = ":/yolotool/app_icon.ico"
SAM_ASSIST_ICON = ASSETS_ROOT / "sam_assist.svg"
SAM_ASSIST_ICON_RESOURCE = ":/yolotool/sam_assist.svg"
