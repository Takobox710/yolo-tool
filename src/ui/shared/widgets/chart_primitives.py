from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QLabel


_BAR_TOP_PADDING = 27
_CHART_FRAME_COLOR = "#CFD9E3"
_CHART_FRAME_RADIUS = 5


def _begin_chart_paint(widget: QLabel, width: int, height: int):
    dpr = max(float(widget.devicePixelRatioF()), 1.0)
    pixmap = QPixmap(max(round(width * dpr), 1), max(round(height * dpr), 1))
    pixmap.fill(Qt.GlobalColor.white)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(dpr, dpr)
    painter.setPen(QPen(QColor(_CHART_FRAME_COLOR), 1))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(
        QRectF(0.5, 0.5, max(width - 1, 1), max(height - 1, 1)),
        _CHART_FRAME_RADIUS,
        _CHART_FRAME_RADIUS,
    )
    return pixmap, painter, dpr


def _finish_chart_paint(widget: QLabel, pixmap: QPixmap, painter: QPainter, dpr: float) -> None:
    painter.end()
    pixmap.setDevicePixelRatio(dpr)
    widget.setPixmap(pixmap)


__all__ = [
    "_BAR_TOP_PADDING",
    "_CHART_FRAME_COLOR",
    "_CHART_FRAME_RADIUS",
    "_begin_chart_paint",
    "_finish_chart_paint",
]