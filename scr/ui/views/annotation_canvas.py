from __future__ import annotations

from pathlib import Path

from PIL import Image
from PySide6.QtCore import QPointF, QRectF, QTimer
from PySide6.QtGui import QAction, QColor, QImage, QKeySequence, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QMenu

from scr.services.editable_annotation_service import EditableAnnotation, _detect_points_to_rect
from scr.ui.qt import QSizePolicy, Qt, QWidget


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


def _pixmap_from_path(path: Path) -> QPixmap:
    image = Image.open(path).convert("RGBA")
    data = image.tobytes("raw", "RGBA")
    qimage = QImage(data, image.width, image.height, image.width * 4, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimage.copy())


class AnnotationCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("annotationCanvas")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setMinimumSize(420, 360)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.image_path: Path | None = None
        self.pixmap: QPixmap | None = None
        self.image_size = (0, 0)
        self.annotations: list[EditableAnnotation] = []
        self.class_names: list[str] = []
        self.current_class_id = 0
        self.draw_shape = "select"
        self.selected_index = -1
        self.hovered_index = -1
        self.drag_start: tuple[float, float] | None = None
        self.drag_current: tuple[float, float] | None = None
        self.obb_first: tuple[float, float] | None = None
        self.obb_second: tuple[float, float] | None = None
        self.polygon_points: list[tuple[float, float]] = []
        self.preview_line_end: tuple[float, float] | None = None
        self.active_handle: tuple[str, int] | None = None
        self.hovered_handle: tuple[str, int] | None = None
        self.move_anchor: tuple[float, float] | None = None
        self.hovered_polygon_close_index = -1
        self.line_expand_enabled = False
        self.line_expand_pixels = 10
        self.continuous_draw = False
        self.quick_draw = True
        self.flash_index = -1
        self.changed_callback = None
        self.selection_callback = None
        self._flash_timer = QTimer(self)
        self._flash_timer.setSingleShot(True)
        self._flash_timer.timeout.connect(self._clear_flash)

    def set_image(
        self,
        image_path: Path | None,
        annotations: list[EditableAnnotation],
        class_names: list[str],
    ) -> None:
        self.image_path = image_path
        self.annotations = annotations
        self.class_names = class_names
        self.selected_index = -1
        self.drag_start = None
        self.drag_current = None
        self.obb_first = None
        self.obb_second = None
        self.polygon_points = []
        self.preview_line_end = None
        self.active_handle = None
        self.hovered_handle = None
        self.hovered_index = -1
        self.hovered_polygon_close_index = -1
        self.move_anchor = None
        self.flash_index = -1
        self._flash_timer.stop()
        if image_path is None:
            self.pixmap = None
            self.image_size = (0, 0)
        else:
            self.pixmap = _pixmap_from_path(image_path)
            self.image_size = (self.pixmap.width(), self.pixmap.height())
        self._emit_selection()
        self.update()

    def set_class_names(self, class_names: list[str]) -> None:
        self.class_names = class_names
        self.update()

    def set_current_class(self, class_id: int) -> None:
        self.current_class_id = max(0, class_id)

    def set_draw_shape(self, shape: str) -> None:
        self.draw_shape = shape
        self.drag_start = None
        self.drag_current = None
        self.obb_first = None
        self.obb_second = None
        self.polygon_points = []
        self.preview_line_end = None
        self.active_handle = None
        self.hovered_handle = None
        self.hovered_polygon_close_index = -1
        self.move_anchor = None
        self.update()

    def set_line_expand_config(self, enabled: bool, pixels: int) -> None:
        self.line_expand_enabled = bool(enabled)
        self.line_expand_pixels = max(1, int(pixels))

    def set_interaction_config(self, continuous_draw: bool, quick_draw: bool) -> None:
        self.continuous_draw = bool(continuous_draw)
        self.quick_draw = bool(quick_draw)

    def delete_selected(self) -> bool:
        if 0 <= self.selected_index < len(self.annotations):
            del self.annotations[self.selected_index]
            self.selected_index = -1
            self._emit_changed()
            self._emit_selection()
            self.update()
            return True
        return False

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
                flashing=index == self.flash_index,
            )
        if self.draw_shape == "line_expand" and self.quick_draw and self.drag_start and self.drag_current:
            preview = self._make_obb_annotation(self.drag_start, self.drag_current, None)
            if preview:
                self._draw_annotation(painter, preview, selected=True)
        elif self.drag_start and self.drag_current:
            preview = self._make_annotation(self.drag_start, self.drag_current)
            if preview:
                self._draw_annotation(painter, preview, selected=True)
        elif self.obb_first and self.obb_second and self.drag_current:
            preview = self._make_obb_annotation(
                self.obb_first, self.obb_second, self.drag_current
            )
            if preview:
                self._draw_annotation(painter, preview, selected=True)
        elif self.obb_first and self.preview_line_end:
            self._draw_preview_polyline(
                painter,
                [self.obb_first, self.preview_line_end],
                closed=False,
            )
        if self.polygon_points:
            preview_points = list(self.polygon_points)
            if self.preview_line_end is not None:
                preview_points.append(self.preview_line_end)
            self._draw_preview_polyline(
                painter,
                preview_points,
                closed=False,
                handle_points=self.polygon_points,
            )

    def mousePressEvent(self, event):  # noqa: N802 - Qt API name
        if self.pixmap is None:
            return
        image_point = self._widget_to_image(event.position())
        if event.button() == Qt.MouseButton.RightButton:
            if image_point is not None:
                hit_index = self._hit_test(image_point)
                if hit_index >= 0:
                    self.selected_index = hit_index
                    self._emit_selection()
                    self.update()
            self._show_context_menu(event.globalPosition().toPoint())
            return
        if event.button() != Qt.MouseButton.LeftButton or image_point is None:
            return
        if self.draw_shape == "select":
            handle = self._hit_handle(image_point)
            if handle is not None:
                self.active_handle = handle
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                self.update()
                return
            hit_index = self._hit_test(image_point)
            if hit_index >= 0:
                self.selected_index = hit_index
                self._emit_selection()
                if hit_index == self.selected_index:
                    self.move_anchor = image_point
                    self.setCursor(Qt.CursorShape.ClosedHandCursor)
                self.update()
                return
            self.selected_index = -1
            self._emit_selection()
            self.update()
            return
        if self.draw_shape in {"obb_mirror", "obb_single", "line_expand"}:
            if self.draw_shape == "line_expand" and self.quick_draw:
                self.drag_start = image_point
                self.drag_current = image_point
                self.update()
                return
            self._handle_rotated_shape_click(image_point)
            self.update()
            return
        if self.draw_shape == "circle":
            if self.quick_draw:
                self.drag_start = image_point
                self.drag_current = image_point
            else:
                self._handle_two_click_shape_click(image_point)
            self.update()
            return
        if self.draw_shape == "polygon":
            self._handle_polygon_click(image_point)
            self.update()
            return
        if self.quick_draw:
            self.drag_start = image_point
            self.drag_current = image_point
        else:
            self._handle_two_click_shape_click(image_point)

    def mouseMoveEvent(self, event):  # noqa: N802 - Qt API name
        image_point = self._widget_to_image(event.position(), clamp=True)
        if self.draw_shape == "select":
            self._update_hover_state(image_point)
        elif self.draw_shape == "polygon":
            self._update_polygon_hover_state(image_point)
        if self.active_handle is not None and 0 <= self.selected_index < len(self.annotations):
            if image_point is not None:
                self._update_selected_handle(image_point)
                self.update()
            return
        if self.move_anchor is not None and 0 <= self.selected_index < len(self.annotations):
            if image_point is not None:
                dx = image_point[0] - self.move_anchor[0]
                dy = image_point[1] - self.move_anchor[1]
                if dx or dy:
                    self._move_selected_annotation(dx, dy)
                    self.move_anchor = image_point
                    self.update()
            return
        if self.draw_shape == "line_expand" and self.quick_draw and self.drag_start is not None:
            self.drag_current = image_point
            self.update()
            return
        if self.obb_first is not None:
            if self.obb_second is not None:
                if image_point is not None:
                    self.drag_current = image_point
                    self.update()
            elif image_point is not None:
                self.preview_line_end = image_point
                self.update()
            return
        if self.polygon_points:
            if image_point is not None:
                self.preview_line_end = image_point
                self.update()
            return
        if self.drag_start is None:
            return
        self.drag_current = image_point
        self.update()

    def mouseReleaseEvent(self, event):  # noqa: N802 - Qt API name
        if self.active_handle is not None:
            self.active_handle = None
            self._emit_changed()
            self._update_hover_cursor()
            self.update()
            return
        if self.move_anchor is not None:
            self.move_anchor = None
            self._emit_changed()
            self._update_hover_cursor()
            self.update()
            return
        if self.draw_shape == "line_expand" and self.quick_draw:
            if event.button() != Qt.MouseButton.LeftButton or self.drag_start is None:
                return
            image_point = self._widget_to_image(event.position())
            if image_point is not None:
                annotation = self._make_obb_annotation(self.drag_start, image_point, None)
                if annotation is not None:
                    self._finish_annotation(annotation)
                else:
                    self._reset_transient_draw_state()
            self.update()
            return
        if self.draw_shape in {"obb_mirror", "obb_single", "line_expand", "polygon"}:
            return
        if not self.quick_draw:
            return
        if event.button() != Qt.MouseButton.LeftButton or self.drag_start is None:
            return
        image_point = self._widget_to_image(event.position())
        if image_point is not None:
            annotation = self._make_annotation(self.drag_start, image_point)
            if annotation is not None:
                self._finish_annotation(annotation)
            else:
                self._reset_transient_draw_state()
        self.update()

    def leaveEvent(self, event):  # noqa: N802 - Qt API name
        super().leaveEvent(event)
        self.hovered_index = -1
        self.hovered_handle = None
        self.hovered_polygon_close_index = -1
        if self.active_handle is None and self.move_anchor is None:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def keyPressEvent(self, event):  # noqa: N802 - Qt API name
        if event.key() == Qt.Key.Key_Delete:
            self.delete_selected()
            return
        if event.key() == Qt.Key.Key_Escape:
            if self._cancel_current_drawing():
                self.update()
                return
        super().keyPressEvent(event)

    def _image_rect(self) -> QRectF:
        if self.pixmap is None or self.pixmap.isNull():
            return QRectF()
        available = self.rect().adjusted(0, 0, 0, 0)
        scale = min(
            available.width() / self.pixmap.width(),
            available.height() / self.pixmap.height(),
        )
        width = self.pixmap.width() * scale
        height = self.pixmap.height() * scale
        left = available.left() + (available.width() - width) / 2
        top = available.top() + (available.height() - height) / 2
        return QRectF(left, top, width, height)

    def _image_to_widget(self, point: tuple[float, float]) -> QPointF:
        target = self._image_rect()
        width, height = self.image_size
        return QPointF(
            target.left() + point[0] / width * target.width(),
            target.top() + point[1] / height * target.height(),
        )

    def _widget_to_image(self, point: QPointF, clamp: bool = False) -> tuple[float, float] | None:
        target = self._image_rect()
        if not clamp and not target.contains(point):
            return None
        width, height = self.image_size
        x_widget = min(max(point.x(), target.left()), target.right())
        y_widget = min(max(point.y(), target.top()), target.bottom())
        x_pos = (x_widget - target.left()) / target.width() * width
        y_pos = (y_widget - target.top()) / target.height() * height
        return (
            max(0.0, min(float(width), x_pos)),
            max(0.0, min(float(height), y_pos)),
        )

    def _make_annotation(
        self, start: tuple[float, float], end: tuple[float, float]
    ) -> EditableAnnotation | None:
        x1, y1 = start
        x2, y2 = end
        if abs(x2 - x1) < 3 or abs(y2 - y1) < 3:
            return None
        left, right = sorted((x1, x2))
        top, bottom = sorted((y1, y2))
        if self.draw_shape == "circle":
            radius = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
            if radius < 3:
                return None
            left = x1 - radius
            right = x1 + radius
            top = y1 - radius
            bottom = y1 + radius
            shape = "circle"
        elif self.draw_shape in {"obb_mirror", "obb_single", "line_expand"}:
            shape = self.draw_shape
        else:
            shape = "rect"
        points = [(left, top), (right, top), (right, bottom), (left, bottom)]
        return EditableAnnotation(self.current_class_id, shape, points)

    def _make_obb_annotation(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        width_point: tuple[float, float] | None,
    ) -> EditableAnnotation | None:
        x1, y1 = start
        x2, y2 = end
        dx = x2 - x1
        dy = y2 - y1
        length = (dx * dx + dy * dy) ** 0.5
        if length < 3:
            return None
        nx = -dy / length
        ny = dx / length
        if self.draw_shape == "line_expand":
            distance = float(self.line_expand_pixels)
            points = [
                (x1 + nx * distance, y1 + ny * distance),
                (x2 + nx * distance, y2 + ny * distance),
                (x2 - nx * distance, y2 - ny * distance),
                (x1 - nx * distance, y1 - ny * distance),
            ]
            return EditableAnnotation(self.current_class_id, "line_expand", points)
        if width_point is None:
            return None
        wx, wy = width_point
        raw_distance = (wx - x1) * nx + (wy - y1) * ny
        distance = abs(raw_distance)
        if distance < 3:
            return None
        if self.draw_shape == "obb_single":
            side = 1.0 if raw_distance >= 0 else -1.0
            points = [
                (x1, y1),
                (x2, y2),
                (x2 + nx * distance * side, y2 + ny * distance * side),
                (x1 + nx * distance * side, y1 + ny * distance * side),
            ]
            return EditableAnnotation(self.current_class_id, "obb_single", points)
        points = [
            (x1 + nx * distance, y1 + ny * distance),
            (x2 + nx * distance, y2 + ny * distance),
            (x2 - nx * distance, y2 - ny * distance),
            (x1 - nx * distance, y1 - ny * distance),
        ]
        shape = "line_expand" if self.draw_shape == "line_expand" else "obb_mirror"
        return EditableAnnotation(self.current_class_id, shape, points)

    def _draw_annotation(
        self,
        painter: QPainter,
        annotation: EditableAnnotation,
        *,
        selected: bool = False,
        hovered: bool = False,
        dashed: bool = False,
        flashing: bool = False,
    ) -> None:
        color = _class_color(annotation.class_id)
        pen = QPen(color, 2 if selected else 1)
        if dashed:
            pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        widget_points = [self._image_to_widget(point) for point in annotation.points]
        if (selected and hovered and not dashed) or flashing:
            fill_color = QColor(255, 120, 120, 72)
            painter.setBrush(fill_color)
            if annotation.shape == "circle":
                x1, y1, x2, y2 = _detect_points_to_rect(annotation.points)
                top_left = self._image_to_widget((x1, y1))
                bottom_right = self._image_to_widget((x2, y2))
                painter.drawEllipse(QRectF(top_left, bottom_right))
            elif annotation.shape == "polygon":
                painter.drawPolygon(QPolygonF(widget_points))
            else:
                painter.drawPolygon(QPolygonF(widget_points))
            painter.setBrush(Qt.BrushStyle.NoBrush)
        if annotation.shape == "circle":
            x1, y1, x2, y2 = _detect_points_to_rect(annotation.points)
            top_left = self._image_to_widget((x1, y1))
            bottom_right = self._image_to_widget((x2, y2))
            painter.drawEllipse(QRectF(top_left, bottom_right))
        else:
            for start, end in zip(widget_points, widget_points[1:] + widget_points[:1]):
                painter.drawLine(start, end)
        label = (
            self.class_names[annotation.class_id]
            if 0 <= annotation.class_id < len(self.class_names)
            else str(annotation.class_id)
        )
        anchor = min(widget_points, key=lambda point: (point.y(), point.x()))
        text_rect = painter.fontMetrics().boundingRect(label)
        label_rect = QRectF(
            anchor.x(),
            max(0.0, anchor.y() - text_rect.height() - 8),
            text_rect.width() + 12,
            text_rect.height() + 6,
        )
        painter.fillRect(label_rect, color)
        painter.setPen(QColor("white"))
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, label)
        if selected and self.draw_shape == "select" and not dashed:
            self._draw_handles(painter, annotation)

    def _draw_preview_polyline(
        self,
        painter: QPainter,
        points: list[tuple[float, float]],
        *,
        closed: bool,
        handle_points: list[tuple[float, float]] | None = None,
    ) -> None:
        if len(points) < 2:
            handle_points = handle_points or points
            self._draw_preview_points(painter, handle_points)
            return
        widget_points = [self._image_to_widget(point) for point in points]
        painter.setPen(QPen(QColor("#B91C1C"), 2))
        for start, end in zip(widget_points, widget_points[1:]):
            painter.drawLine(start, end)
        if closed:
            painter.drawLine(widget_points[-1], widget_points[0])
        self._draw_preview_points(painter, handle_points or points)

    def _draw_preview_points(
        self,
        painter: QPainter,
        points: list[tuple[float, float]],
    ) -> None:
        radius = max(2.5, self._handle_radius() - 0.75)
        painter.setPen(QPen(QColor("#B91C1C"), 2))
        for index, point in enumerate(points):
            widget_point = self._image_to_widget(point)
            is_closing_target = index == self.hovered_polygon_close_index
            fill = QColor("#FFCACA") if is_closing_target else QColor("#FFFFFF")
            painter.setBrush(fill)
            painter.drawEllipse(
                QRectF(
                    widget_point.x() - radius,
                    widget_point.y() - radius,
                    radius * 2,
                    radius * 2,
                )
            )
        painter.setBrush(Qt.BrushStyle.NoBrush)

    def _hit_test(self, point: tuple[float, float]) -> int:
        for index in range(len(self.annotations) - 1, -1, -1):
            x1, y1, x2, y2 = _detect_points_to_rect(self.annotations[index].points)
            margin = max(4.0, min(self.image_size or (4, 4)) * 0.005)
            if x1 - margin <= point[0] <= x2 + margin and y1 - margin <= point[1] <= y2 + margin:
                return index
        return -1

    def _handle_radius(self) -> float:
        return max(3.0, min(self.image_size or (200, 200)) * 0.006)

    def _annotation_handles(self, annotation: EditableAnnotation) -> list[tuple[str, tuple[float, float]]]:
        if annotation.shape == "circle":
            x1, y1, x2, y2 = _detect_points_to_rect(annotation.points)
            center = ((x1 + x2) / 2, (y1 + y2) / 2)
            radius = max((x2 - x1) / 2, (y2 - y1) / 2)
            return [("center", center), ("radius", (center[0] + radius, center[1]))]
        return [(f"point-{index}", point) for index, point in enumerate(annotation.points)]

    def _draw_handles(self, painter: QPainter, annotation: EditableAnnotation) -> None:
        radius = self._handle_radius()
        for handle_type, point in self._annotation_handles(annotation):
            widget_point = self._image_to_widget(point)
            fill = QColor("#FFFFFF")
            if annotation.shape == "circle" and handle_type == "center":
                fill = QColor("#FFE3E3")
            painter.setPen(QPen(QColor("#B91C1C"), 2))
            painter.setBrush(fill)
            if self.hovered_index == self.selected_index:
                painter.drawRect(QRectF(widget_point.x() - radius, widget_point.y() - radius, radius * 2, radius * 2))
            else:
                painter.drawEllipse(QRectF(widget_point.x() - radius, widget_point.y() - radius, radius * 2, radius * 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)

    def _hit_handle(self, point: tuple[float, float]) -> tuple[str, int] | None:
        if not (0 <= self.selected_index < len(self.annotations)):
            return None
        radius = self._handle_radius() * 1.6
        annotation = self.annotations[self.selected_index]
        for handle_type, handle_point in self._annotation_handles(annotation):
            dx = point[0] - handle_point[0]
            dy = point[1] - handle_point[1]
            if dx * dx + dy * dy <= radius * radius:
                if handle_type.startswith("point-"):
                    return ("point", int(handle_type.split("-", 1)[1]))
                if handle_type == "center":
                    return ("center", 0)
                if handle_type == "radius":
                    return ("radius", 0)
        return None

    def _update_selected_handle(self, point: tuple[float, float]) -> None:
        if self.active_handle is None or not (0 <= self.selected_index < len(self.annotations)):
            return
        annotation = self.annotations[self.selected_index]
        handle_type, handle_index = self.active_handle
        if annotation.shape == "circle":
            x1, y1, x2, y2 = _detect_points_to_rect(annotation.points)
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            radius = max((x2 - x1) / 2, (y2 - y1) / 2)
            if handle_type == "center":
                center_x, center_y = point
            elif handle_type == "radius":
                radius = max(3.0, ((point[0] - center_x) ** 2 + (point[1] - center_y) ** 2) ** 0.5)
            annotation.points = [
                (center_x - radius, center_y - radius),
                (center_x + radius, center_y - radius),
                (center_x + radius, center_y + radius),
                (center_x - radius, center_y + radius),
            ]
            return
        if annotation.shape == "rect" and handle_type == "point":
            opposite = annotation.points[(handle_index + 2) % 4]
            left, right = sorted((point[0], opposite[0]))
            top, bottom = sorted((point[1], opposite[1]))
            annotation.points = [
                (left, top),
                (right, top),
                (right, bottom),
                (left, bottom),
            ]
            return
        if annotation.shape in {"obb", "obb_mirror", "obb_single", "line_expand"} and handle_type == "point":
            rect_points = self._rebuild_rotated_rect_from_corner(annotation.points, handle_index, point)
            if rect_points is not None:
                annotation.points = rect_points
            return
        if handle_type == "point" and 0 <= handle_index < len(annotation.points):
            annotation.points[handle_index] = point

    def _move_selected_annotation(self, dx: float, dy: float) -> None:
        if not (0 <= self.selected_index < len(self.annotations)):
            return
        annotation = self.annotations[self.selected_index]
        annotation.points = [(x_pos + dx, y_pos + dy) for x_pos, y_pos in annotation.points]

    def _rebuild_rotated_rect_from_corner(
        self,
        points: list[tuple[float, float]],
        corner_index: int,
        moved_point: tuple[float, float],
    ) -> list[tuple[float, float]] | None:
        if len(points) != 4:
            return None
        p0, p1, p2, p3 = points
        ux = p1[0] - p0[0]
        uy = p1[1] - p0[1]
        vx = p3[0] - p0[0]
        vy = p3[1] - p0[1]
        u_len = (ux * ux + uy * uy) ** 0.5
        v_len = (vx * vx + vy * vy) ** 0.5
        if u_len < 1 or v_len < 1:
            return None
        ux /= u_len
        uy /= u_len
        vx /= v_len
        vy /= v_len
        opposite_index = (corner_index + 2) % 4
        fixed = points[opposite_index]
        dx = moved_point[0] - fixed[0]
        dy = moved_point[1] - fixed[1]
        proj_u = dx * ux + dy * uy
        proj_v = dx * vx + dy * vy
        if abs(proj_u) < 3 or abs(proj_v) < 3:
            return None
        corner = moved_point
        corner_u = (fixed[0] + proj_u * ux, fixed[1] + proj_u * uy)
        corner_v = (fixed[0] + proj_v * vx, fixed[1] + proj_v * vy)
        if corner_index == 0:
            return [corner, corner_v, fixed, corner_u]
        if corner_index == 1:
            return [corner_v, corner, corner_u, fixed]
        if corner_index == 2:
            return [fixed, corner_u, corner, corner_v]
        return [corner_u, fixed, corner_v, corner]

    def _update_hover_state(self, point: tuple[float, float] | None) -> None:
        if point is None:
            self.hovered_index = -1
            self.hovered_handle = None
            self._update_hover_cursor()
            self.update()
            return
        previous_index = self.hovered_index
        previous_handle = self.hovered_handle
        self.hovered_handle = self._hit_handle(point)
        if self.hovered_handle is not None:
            self.hovered_index = self.selected_index
        else:
            self.hovered_index = self._hit_test(point)
        self._update_hover_cursor()
        if previous_index != self.hovered_index or previous_handle != self.hovered_handle:
            self.update()

    def _update_hover_cursor(self) -> None:
        if self.active_handle is not None or self.move_anchor is not None:
            return
        if self.draw_shape == "select" and (self.hovered_handle is not None or self.hovered_index >= 0):
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        elif self.draw_shape == "polygon" and self.hovered_polygon_close_index >= 0:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def _update_polygon_hover_state(self, point: tuple[float, float] | None) -> None:
        previous_index = self.hovered_polygon_close_index
        self.hovered_polygon_close_index = -1
        if point is not None:
            closing_index = self._polygon_closing_index(point)
            if closing_index is not None and len(self.polygon_points) >= 3:
                if closing_index == 0 or closing_index >= 2:
                    self.hovered_polygon_close_index = closing_index
        self._update_hover_cursor()
        if previous_index != self.hovered_polygon_close_index:
            self.update()

    def _cancel_current_drawing(self) -> bool:
        if self.drag_start is not None or self.obb_first is not None or self.polygon_points:
            self._reset_transient_draw_state()
            return True
        if self.draw_shape != "select":
            self.set_draw_shape("select")
            return True
        return False

    def _reset_transient_draw_state(self) -> None:
        self.drag_start = None
        self.drag_current = None
        self.obb_first = None
        self.obb_second = None
        self.preview_line_end = None
        self.polygon_points = []
        self.hovered_polygon_close_index = -1
        self.active_handle = None
        self.move_anchor = None

    def _finish_annotation(self, annotation: EditableAnnotation, *, flash: bool = False) -> None:
        self.annotations.append(annotation)
        self.selected_index = len(self.annotations) - 1
        self._emit_changed()
        self._emit_selection()
        if flash:
            self._flash_annotation(self.selected_index)
        if self.continuous_draw:
            self._reset_transient_draw_state()
        else:
            self.set_draw_shape("select")

    def _handle_two_click_shape_click(self, image_point: tuple[float, float]) -> None:
        if self.drag_start is None:
            self.drag_start = image_point
            self.drag_current = image_point
            return
        annotation = self._make_annotation(self.drag_start, image_point)
        if annotation is not None:
            self._finish_annotation(annotation)
        else:
            self._reset_transient_draw_state()

    def _handle_rotated_shape_click(self, image_point: tuple[float, float]) -> None:
        if self.obb_first is None:
            self.obb_first = image_point
            self.obb_second = None
            self.preview_line_end = image_point
            return
        if self.draw_shape == "line_expand":
            annotation = self._make_obb_annotation(self.obb_first, image_point, None)
            if annotation is not None:
                self._finish_annotation(annotation)
            else:
                self._reset_transient_draw_state()
            return
        if self.obb_second is None:
            self.obb_second = image_point
            self.drag_current = image_point
            self.preview_line_end = None
            return
        annotation = self._make_obb_annotation(
            self.obb_first,
            self.obb_second,
            image_point,
        )
        if annotation is not None:
            self._finish_annotation(annotation)
        else:
            self._reset_transient_draw_state()

    def _handle_polygon_click(self, image_point: tuple[float, float]) -> None:
        closing_index = self._polygon_closing_index(image_point)
        if closing_index is not None and (
            closing_index == 0 or closing_index >= 2
        ) and len(self.polygon_points) >= 3:
            points = list(self.polygon_points)
            if closing_index != 0:
                points = points[: closing_index + 1]
            annotation = EditableAnnotation(self.current_class_id, "polygon", points)
            self._finish_annotation(annotation, flash=True)
            return
        self.polygon_points.append(image_point)
        self.preview_line_end = image_point

    def _polygon_closing_index(self, image_point: tuple[float, float]) -> int | None:
        radius_sq = max(36.0, self._handle_radius() ** 2 * 4)
        for index, point in enumerate(self.polygon_points):
            dx = image_point[0] - point[0]
            dy = image_point[1] - point[1]
            if dx * dx + dy * dy <= radius_sq:
                return index
        return None

    def _flash_annotation(self, index: int) -> None:
        self.flash_index = index
        self._flash_timer.start(180)

    def _clear_flash(self) -> None:
        self.flash_index = -1
        self.update()

    def _emit_changed(self) -> None:
        if self.changed_callback:
            self.changed_callback()

    def _emit_selection(self) -> None:
        if self.selection_callback:
            self.selection_callback(self.selected_index)

    def _show_context_menu(self, global_pos) -> None:
        menu = QMenu(self)
        menu.setSeparatorsCollapsible(False)
        select_action = QAction("选择", menu)
        select_action.setCheckable(True)
        select_action.setChecked(self.draw_shape == "select")
        select_action.setShortcut(QKeySequence("V"))
        select_action.setShortcutVisibleInContextMenu(True)
        menu.addAction(select_action)
        separator_top = QAction(menu)
        separator_top.setSeparator(True)
        menu.addAction(separator_top)
        shape_actions: dict[QAction, str] = {}
        for title, shape, shortcut in [
            ("矩形框", "rect", "R"),
            ("有向矩形", "obb_single", "O"),
            ("镜像有向矩形", "obb_mirror", "M"),
            ("多边形", "polygon", "P"),
            ("圆形", "circle", "C"),
        ]:
            action = QAction(title, menu)
            action.setCheckable(True)
            action.setChecked(self.draw_shape == shape)
            action.setShortcut(QKeySequence(shortcut))
            action.setShortcutVisibleInContextMenu(True)
            menu.addAction(action)
            shape_actions[action] = shape
        if self.line_expand_enabled:
            line_expand_action = QAction("直线拓展", menu)
            line_expand_action.setCheckable(True)
            line_expand_action.setChecked(self.draw_shape == "line_expand")
            line_expand_action.setShortcut(QKeySequence("L"))
            line_expand_action.setShortcutVisibleInContextMenu(True)
            menu.addAction(line_expand_action)
            shape_actions[line_expand_action] = "line_expand"
        class_actions: dict[QAction, int] = {}
        if 0 <= self.selected_index < len(self.annotations):
            class_menu = menu.addMenu("标注类别")
            for index, class_name in enumerate(self.class_names):
                action = QAction(f"{index} : {class_name}", class_menu)
                action.setCheckable(True)
                action.setChecked(self.annotations[self.selected_index].class_id == index)
                class_menu.addAction(action)
                class_actions[action] = index
        separator_bottom = QAction(menu)
        separator_bottom.setSeparator(True)
        menu.addAction(separator_bottom)
        delete_action = QAction("删除选中框", menu)
        delete_action.setEnabled(0 <= self.selected_index < len(self.annotations))
        delete_action.setShortcut(QKeySequence(Qt.Key.Key_Delete))
        delete_action.setShortcutVisibleInContextMenu(True)
        menu.addAction(delete_action)
        cancel_action = QAction("取消当前绘制", menu)
        cancel_action.setEnabled(
            self.drag_start is not None
            or self.obb_first is not None
            or bool(self.polygon_points)
            or self.active_handle is not None
            or self.move_anchor is not None
        )
        cancel_action.setShortcut(QKeySequence(Qt.Key.Key_Escape))
        cancel_action.setShortcutVisibleInContextMenu(True)
        menu.addAction(cancel_action)
        selected = menu.exec(global_pos)
        if selected is None:
            return
        if selected == select_action:
            self.set_draw_shape("select")
        elif selected == delete_action:
            self.delete_selected()
        elif selected == cancel_action:
            self._reset_transient_draw_state()
            self.update()
        elif selected in class_actions and 0 <= self.selected_index < len(self.annotations):
            self.annotations[self.selected_index].class_id = class_actions[selected]
            self._emit_changed()
            self.update()
        elif selected in shape_actions:
            self.set_draw_shape(shape_actions[selected])
