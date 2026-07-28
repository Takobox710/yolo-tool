from __future__ import annotations

from src.shared.paths import (
    ICON_PNG,
    ICON_PNG_RESOURCE,
    SAM_ASSIST_ICON,
    SAM_ASSIST_ICON_RESOURCE,
)
from src.shared.qt import QIcon, QPixmap


def _register_embedded_assets() -> None:
    try:
        from src import assets_rc  # noqa: F401
    except ImportError:
        pass


def load_app_icon() -> QIcon:
    _register_embedded_assets()
    icon = QIcon(ICON_PNG_RESOURCE)
    if not icon.isNull():
        return icon
    return QIcon(str(ICON_PNG)) if ICON_PNG.exists() else QIcon()


def load_sam_assist_icon() -> QIcon:
    _register_embedded_assets()
    icon = QIcon(SAM_ASSIST_ICON_RESOURCE)
    if not icon.isNull():
        return icon
    return QIcon(str(SAM_ASSIST_ICON)) if SAM_ASSIST_ICON.exists() else QIcon()


def load_app_pixmap(size: int, device_pixel_ratio: float = 1.0) -> QPixmap:
    icon = load_app_icon()
    dpr = max(float(device_pixel_ratio), 1.0)
    pixmap = icon.pixmap(max(1, round(size * dpr)), max(1, round(size * dpr)))
    if not pixmap.isNull():
        pixmap.setDevicePixelRatio(dpr)
    return pixmap
