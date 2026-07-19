from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from src.shared.qt import Qt


SHORT_CURSOR_CLEARANCE = 20.0
CROSSHAIR_MAX_GRAY = 72
PREVIEW_COLOR = QColor(0, 255, 0, 128)
PREVIEW_FILL_COLOR = QColor(0, 255, 0, 64)


def _class_color(class_id: int) -> QColor:
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


class AnnotationCanvasRenderMixin:
    def paintEvent(self, event):  # noqa: N802 - Qt API name
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#F2F5F9"))
        if self.pixmap is None:
            painter.setPen(QColor("#26394D"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "请打开图片文件夹")
            return
        target = self._image_rect()
        painter.drawPixmap(target, self.pixmap, QRectF(self.pixmap.rect()))
        painter.setPen(QPen(QColor("#D9E3EC"), 1))
        painter.drawRect(target)
        for index, annotation in enumerate(self.annotations):
            self._draw_annotation(
                painter,
                annotation,
                selected=index == self.selected_index,
                hovered=index == self.hovered_index,
                hovered_handle=self.hovered_handle if index == self.hovered_index else None,
                flashing=index == self.flash_index,
                show_label=self.show_annotation_names,
            )
        if self.draw_shape == "line_expand" and self.quick_draw and self.drag_start and self.drag_current:
            preview = self._make_obb_annotation(self.drag_start, self.drag_current, None)
            if preview:
                self._draw_annotation(painter, preview, preview=True, selected=True, show_label=False)
        elif self.drag_start and self.drag_current:
            preview = self._make_annotation(self.drag_start, self.drag_current)
            if preview:
                self._draw_annotation(painter, preview, preview=True, selected=True, show_label=False)
        elif self.obb_first and self.obb_second and self.drag_current:
            preview = self._make_obb_annotation(self.obb_first, self.obb_second, self.drag_current)
            if preview:
                self._draw_annotation(painter, preview, preview=True, selected=True, show_label=False)
        elif self.obb_first and self.preview_line_end:
            self._draw_preview_polyline(painter, [self.obb_first, self.preview_line_end], closed=False)
        if self.polygon_points:
            preview_points = list(self.polygon_points)
            if self.preview_line_end is not None:
                preview_points.append(self.preview_line_end)
            self._draw_preview_polyline(
                painter,
                preview_points,
                closed=False,
                handle_points=self.polygon_points,
                fill=True,
            )
        if self.draw_shape == "rect" and self.crosshair_position is not None:
            self._draw_rect_crosshair(painter)

    def _draw_rect_crosshair(self, painter: QPainter) -> None:
        x_pos, y_pos = self.crosshair_position
        pen = QPen(self._crosshair_color(), 1, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        half_clearance = SHORT_CURSOR_CLEARANCE / 2
        horizontal_left = max(0.0, x_pos - half_clearance)
        horizontal_right = min(float(self.width()), x_pos + half_clearance)
        vertical_top = max(0.0, y_pos - half_clearance)
        vertical_bottom = min(float(self.height()), y_pos + half_clearance)
        if horizontal_left > 0:
            painter.drawLine(QPointF(0, y_pos), QPointF(horizontal_left, y_pos))
        if horizontal_right < self.width():
            painter.drawLine(QPointF(horizontal_right, y_pos), QPointF(float(self.width()), y_pos))
        if vertical_top > 0:
            painter.drawLine(QPointF(x_pos, 0), QPointF(x_pos, vertical_top))
        if vertical_bottom < self.height():
            painter.drawLine(QPointF(x_pos, vertical_bottom), QPointF(x_pos, float(self.height())))

    def _crosshair_color(self) -> QColor:
        if self.pixmap is None or self.crosshair_position is None:
            return QColor("#404040")
        image_point = self._widget_to_image(QPointF(*self.crosshair_position), clamp=True)
        image = self.pixmap.toImage()
        x_pos = min(max(round(image_point[0]), 0), image.width() - 1)
        y_pos = min(max(round(image_point[1]), 0), image.height() - 1)
        background = image.pixelColor(x_pos, y_pos)
        luminance = 0.2126 * background.red() + 0.7152 * background.green() + 0.0722 * background.blue()
        gray = round((255 - luminance) * CROSSHAIR_MAX_GRAY / 255)
        return QColor(gray, gray, gray)

    def _draw_annotation(
        self,
        painter: QPainter,
        annotation,
        *,
        selected: bool = False,
        hovered: bool = False,
        hovered_handle: tuple[str, int] | None = None,
        dashed: bool = False,
        flashing: bool = False,
        preview: bool = False,
        show_label: bool = True,
    ) -> None:
        color = PREVIEW_COLOR if preview else _class_color(annotation.class_id)
        pen = QPen(color, 2 if selected else 1)
        if dashed:
            pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        fill = QColor(color)
        if flashing:
            fill.setAlpha(90)
        elif selected and not preview:
            fill.setAlpha(90)
        elif hovered:
            fill.setAlpha(90)
        else:
            fill.setAlpha(0)
        painter.setBrush(fill)
        points = [self._image_to_widget(point) for point in annotation.points]
        if annotation.shape == "circle":
            x1, y1, x2, y2 = self._detect_points_to_rect(annotation.points)
            top_left = self._image_to_widget((x1, y1))
            bottom_right = self._image_to_widget((x2, y2))
            painter.drawEllipse(QRectF(top_left, bottom_right))
        elif annotation.shape == "polygon":
            painter.drawPolygon(QPolygonF(points))
        else:
            painter.drawPolygon(QPolygonF(points))
        if show_label:
            label = (
                self.class_names[annotation.class_id]
                if 0 <= annotation.class_id < len(self.class_names)
                else str(annotation.class_id)
            )
            if points:
                anchor = points[0]
                painter.setPen(QColor("#FFFFFF"))
                painter.setBrush(color)
                text_rect = painter.fontMetrics().boundingRect(label).adjusted(-6, -3, 6, 3)
                label_rect = QRectF(
                    anchor.x(),
                    anchor.y() - text_rect.height() - 2,
                    text_rect.width(),
                    text_rect.height(),
                )
                painter.drawRect(label_rect)
                painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, label)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        self._draw_handles(
            painter,
            annotation,
            preview=preview,
            hovered_handle=hovered_handle if self.draw_shape == "select" else None,
        )

    def _draw_preview_polyline(
        self,
        painter: QPainter,
        points: list[tuple[float, float]],
        *,
        closed: bool,
        handle_points: list[tuple[float, float]] | None = None,
        fill: bool = False,
    ) -> None:
        if len(points) < 2:
            return
        painter.setPen(QPen(PREVIEW_COLOR, 2))
        widget_points = [self._image_to_widget(point) for point in points]
        if closed or (fill and len(points) >= 3):
            if fill:
                painter.setBrush(PREVIEW_FILL_COLOR)
            painter.drawPolygon(QPolygonF(widget_points))
            painter.setBrush(Qt.BrushStyle.NoBrush)
        else:
            painter.drawPolyline(QPolygonF(widget_points))
        if handle_points:
            self._draw_preview_points(painter, handle_points)

    def _draw_preview_points(self, painter: QPainter, points: list[tuple[float, float]]) -> None:
        painter.setPen(QPen(PREVIEW_COLOR, 2))
        painter.setBrush(QColor("#FFFFFF"))
        radius = self._handle_radius()
        for point in points:
            widget_point = self._image_to_widget(point)
            painter.drawEllipse(
                QRectF(widget_point.x() - radius, widget_point.y() - radius, radius * 2, radius * 2)
            )
        painter.setBrush(Qt.BrushStyle.NoBrush)

    def _draw_handles(
        self,
        painter: QPainter,
        annotation,
        *,
        preview: bool = False,
        hovered_handle: tuple[str, int] | None = None,
    ) -> None:
        radius = self._handle_radius()
        for handle_type, point in self._annotation_handles(annotation):
            widget_point = self._image_to_widget(point)
            fill = QColor("#FFFFFF")
            if annotation.shape == "circle" and handle_type == "center":
                fill = QColor("#FFE3E3")
            handle_color = PREVIEW_COLOR if preview else QColor("#B91C1C")
            painter.setPen(QPen(handle_color, 2))
            painter.setBrush(fill)
            if not preview and self._is_hovered_handle(handle_type, hovered_handle):
                painter.drawRect(QRectF(widget_point.x() - radius, widget_point.y() - radius, radius * 2, radius * 2))
            else:
                painter.drawEllipse(QRectF(widget_point.x() - radius, widget_point.y() - radius, radius * 2, radius * 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)

    @staticmethod
    def _is_hovered_handle(handle_type: str, hovered_handle: tuple[str, int] | None) -> bool:
        if hovered_handle is None:
            return False
        if handle_type.startswith("point-"):
            return hovered_handle == ("point", int(handle_type.split("-", 1)[1]))
        return hovered_handle == (handle_type, 0)
