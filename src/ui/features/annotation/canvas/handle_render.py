from __future__ import annotations

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPainter, QPen
from src.shared.qt import Qt


PREVIEW_COLOR = QColor(0, 255, 0, 128)
PREVIEW_POINT_COLOR = QColor(0, 255, 0)
SOLID_HANDLE_RADIUS = 3.5


def class_color(class_id: int) -> QColor:
    colors = [
        QColor(255, 56, 56),
        QColor(255, 157, 151),
        QColor(255, 112, 31),
        QColor(255, 178, 29),
        QColor(72, 249, 10),
        QColor(61, 219, 134),
        QColor(0, 212, 187),
        QColor(0, 194, 255),
        QColor(100, 115, 255),
        QColor(203, 56, 255),
    ]
    return colors[class_id % len(colors)]


class AnnotationCanvasHandleRenderMixin:
    def _draw_handles(
        self,
        painter: QPainter,
        annotation,
        *,
        preview: bool = False,
        hovered_handle: tuple[str, int] | None = None,
        handle_reference_point: tuple[float, float] | None = None,
    ) -> None:
        radius = self._handle_radius()
        for handle_type, point in self._annotation_handles(annotation, reference_point=handle_reference_point):
            widget_point = self._image_to_widget(point)
            handle_color = PREVIEW_COLOR if preview else class_color(annotation.class_id)
            hollow = not preview and hovered_handle is not None
            is_hovered = hollow and self._is_hovered_handle(handle_type, hovered_handle)
            if hollow:
                fill = QColor("#FFFFFF")
                radius = self._handle_radius()
            else:
                fill = PREVIEW_POINT_COLOR if preview else handle_color
                radius = SOLID_HANDLE_RADIUS
            painter.setPen(QPen(handle_color, 2))
            painter.setBrush(fill)
            bounds = QRectF(widget_point.x() - radius, widget_point.y() - radius, radius * 2, radius * 2)
            if hollow and is_hovered:
                painter.drawRect(bounds)
            else:
                painter.drawEllipse(bounds)
        painter.setBrush(Qt.BrushStyle.NoBrush)

    @staticmethod
    def _is_hovered_handle(handle_type: str, hovered_handle: tuple[str, int] | None) -> bool:
        if hovered_handle is None:
            return False
        if handle_type.startswith("point-"):
            return hovered_handle == ("point", int(handle_type.split("-", 1)[1]))
        if handle_type.startswith("rotate-"):
            return hovered_handle == ("rotate", int(handle_type.split("-", 1)[1]))
        if handle_type.startswith("mirror-center-"):
            return hovered_handle == ("mirror-center", int(handle_type.rsplit("-", 1)[1]))
        if handle_type.startswith("mirror-width-"):
            return hovered_handle == ("mirror-width", int(handle_type.rsplit("-", 1)[1]))
        return hovered_handle == (handle_type, 0)
