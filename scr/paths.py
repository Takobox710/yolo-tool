from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = Path(__file__).resolve().parent
RUNTIME_ROOT = PACKAGE_ROOT / "runtime"
ASSETS_ROOT = PACKAGE_ROOT / "assets"
DEFAULT_SETTINGS_PATH = RUNTIME_ROOT / "settings.json"
ICON_PNG = ASSETS_ROOT / "app_icon.png"
ICON_ICO = ASSETS_ROOT / "app_icon.ico"
