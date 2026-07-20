from __future__ import annotations

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPainter
from src.shared.qt import Qt


STATUS_MARGIN = 10.0
STATUS_HORIZONTAL_PADDING = 8.0
STATUS_VERTICAL_PADDING = 4.0
DRAW_SHAPE_LABELS = {
    "select": "编辑",
    "rect": "矩形框",
    "obb_single": "有向矩形",
    "obb_mirror": "镜像有向矩形",
    "polygon": "多边形",
    "circle": "圆形",
    "line_expand": "直线扩展",
}


class AnnotationCanvasStatusMixin:
    def _draw_canvas_status_if_enabled(self, painter: QPainter) -> None:
        if self.show_canvas_status:
            self._draw_canvas_status(painter)

    def _canvas_status_text(self) -> str:
        return DRAW_SHAPE_LABELS.get(self.draw_shape, self.draw_shape)

    def _draw_canvas_status(self, painter: QPainter) -> None:
        label = self._canvas_status_text()
        metrics = painter.fontMetrics()
        text_bounds = metrics.boundingRect(label)
        box_width = text_bounds.width() + STATUS_HORIZONTAL_PADDING * 2
        box_height = text_bounds.height() + STATUS_VERTICAL_PADDING * 2
        status_rect = QRectF(
            STATUS_MARGIN,
            self.height() - STATUS_MARGIN - box_height,
            box_width,
            box_height,
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(20, 35, 58, 190))
        painter.drawRoundedRect(status_rect, 4, 4)
        painter.setPen(QColor("#FFFFFF"))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawText(status_rect, Qt.AlignmentFlag.AlignCenter, label)
