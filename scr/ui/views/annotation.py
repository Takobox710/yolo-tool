from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from scr.services.rename_service import natural_sort_key
from scr.services.annotation_ai_service import (
    available_ai_models,
    collect_ai_target_images,
    resolve_ai_model_path,
)
from scr.ui.helpers import _find_models_full_paths, _simplified_model_path
from scr.ui.page_base import BasePage, _IMAGE_SUFFIXES
from scr.ui.qt import (
    QAbstractItemView,
    QButtonGroup,
    QGridLayout,
    QComboBox,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QShortcut,
    QSizePolicy,
    QSpinBox,
    QStyle,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    Qt,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import QEvent, QPoint, QPointF, QRectF, QTimer
from PySide6.QtGui import QAction, QColor, QImage, QKeySequence, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QMenu
import threading

from scr.ui.workers import AnnotationAiWorker, ModelLabelsWorker


@dataclass
class EditableAnnotation:
    class_id: int
    shape: str
    points: list[tuple[float, float]]


_SHAPE_LABELS = {
    "rect": "矩形框",
    "circle": "圆形",
    "obb": "有向矩形",
    "obb_mirror": "镜像有向矩形",
    "obb_single": "有向矩形",
    "polygon": "多边形",
    "line_expand": "直线拓展",
}


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


def _detect_points_to_rect(points: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def load_editable_annotations(
    image_size: tuple[int, int], label_path: Path
) -> list[EditableAnnotation]:
    width, height = image_size
    annotations: list[EditableAnnotation] = []
    if not label_path.exists():
        return annotations
    for raw_line in label_path.read_text(encoding="utf-8").splitlines():
        parts = raw_line.strip().split()
        if len(parts) < 5:
            continue
        try:
            class_id = int(float(parts[0]))
            values = [float(item) for item in parts[1:]]
        except ValueError:
            continue
        if len(values) >= 8:
            points = [
                (values[index] * width, values[index + 1] * height)
                for index in range(0, 8, 2)
            ]
            annotations.append(EditableAnnotation(class_id, "obb", points))
        elif len(values) >= 4:
            cx, cy, box_w, box_h = values[:4]
            x_center = cx * width
            y_center = cy * height
            half_w = box_w * width / 2
            half_h = box_h * height / 2
            points = [
                (x_center - half_w, y_center - half_h),
                (x_center + half_w, y_center - half_h),
                (x_center + half_w, y_center + half_h),
                (x_center - half_w, y_center + half_h),
            ]
            annotations.append(EditableAnnotation(class_id, "rect", points))
    return annotations


def _labelme_class_id(label: str, class_names: list[str]) -> int:
    text = str(label or "").strip()
    if not text:
        text = "weld"
    if text in class_names:
        return class_names.index(text)
    class_names.append(text)
    return len(class_names) - 1


def _line_points_to_obb(
    points: list[tuple[float, float]], half_width: float
) -> list[tuple[float, float]] | None:
    if len(points) != 2:
        return None
    (x1, y1), (x2, y2) = points
    dx = x2 - x1
    dy = y2 - y1
    length = (dx * dx + dy * dy) ** 0.5
    if length < 1:
        return None
    nx = -dy / length
    ny = dx / length
    return [
        (x1 + nx * half_width, y1 + ny * half_width),
        (x2 + nx * half_width, y2 + ny * half_width),
        (x2 - nx * half_width, y2 - ny * half_width),
        (x1 - nx * half_width, y1 - ny * half_width),
    ]


def load_labelme_annotations(
    image_size: tuple[int, int],
    json_path: Path,
    class_names: list[str],
    line_expand_pixels: int = 10,
) -> tuple[list[EditableAnnotation], list[str]]:
    annotations: list[EditableAnnotation] = []
    names = list(class_names) or ["weld"]
    if not json_path.exists():
        return annotations, names
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return annotations, names

    for shape in payload.get("shapes", []):
        raw_points = shape.get("points", [])
        points: list[tuple[float, float]] = []
        for point in raw_points:
            if not isinstance(point, (list, tuple)) or len(point) < 2:
                continue
            try:
                points.append((float(point[0]), float(point[1])))
            except (TypeError, ValueError):
                continue
        if not points:
            continue
        class_id = _labelme_class_id(str(shape.get("label") or ""), names)
        shape_type = str(shape.get("shape_type") or "").strip()
        if shape_type == "rectangle" and len(points) >= 2:
            (x1, y1), (x2, y2) = points[:2]
            left, right = sorted((x1, x2))
            top, bottom = sorted((y1, y2))
            annotations.append(
                EditableAnnotation(
                    class_id,
                    "rect",
                    [(left, top), (right, top), (right, bottom), (left, bottom)],
                )
            )
        elif shape_type == "circle" and len(points) >= 2:
            center = points[0]
            edge = points[1]
            radius = ((edge[0] - center[0]) ** 2 + (edge[1] - center[1]) ** 2) ** 0.5
            annotations.append(
                EditableAnnotation(
                    class_id,
                    "circle",
                    [
                        (center[0] - radius, center[1] - radius),
                        (center[0] + radius, center[1] - radius),
                        (center[0] + radius, center[1] + radius),
                        (center[0] - radius, center[1] + radius),
                    ],
                )
            )
        elif shape_type == "line":
            obb_points = _line_points_to_obb(points[:2], float(line_expand_pixels))
            if obb_points is not None:
                annotations.append(EditableAnnotation(class_id, "line_expand", obb_points))
        elif shape_type == "oriented_rectangle" and len(points) >= 4:
            annotations.append(EditableAnnotation(class_id, "obb", points[:4]))
        elif shape_type == "polygon" and len(points) >= 3:
            annotations.append(EditableAnnotation(class_id, "polygon", points))
        elif len(points) >= 4:
            annotations.append(EditableAnnotation(class_id, "polygon", points))
        elif len(points) >= 2:
            left, top, right, bottom = _detect_points_to_rect(points)
            annotations.append(
                EditableAnnotation(
                    class_id,
                    "rect",
                    [(left, top), (right, top), (right, bottom), (left, bottom)],
                )
            )
    return annotations, names


def save_labelme_annotations(
    image_size: tuple[int, int],
    json_path: Path,
    image_path: Path,
    annotations: list[EditableAnnotation],
    class_names: list[str],
) -> None:
    width, height = image_size
    shapes: list[dict] = []
    for annotation in annotations:
        label = (
            class_names[annotation.class_id]
            if 0 <= annotation.class_id < len(class_names)
            else str(annotation.class_id)
        )
        points = annotation.points
        shape_type = "polygon"
        labelme_points = [[float(x_pos), float(y_pos)] for x_pos, y_pos in points]
        if annotation.shape == "rect":
            x1, y1, x2, y2 = _detect_points_to_rect(points)
            shape_type = "rectangle"
            labelme_points = [[float(x1), float(y1)], [float(x2), float(y2)]]
        elif annotation.shape == "circle":
            x1, y1, x2, y2 = _detect_points_to_rect(points)
            center = ((x1 + x2) / 2, (y1 + y2) / 2)
            radius = max(abs(x2 - x1), abs(y2 - y1)) / 2
            shape_type = "circle"
            labelme_points = [
                [float(center[0]), float(center[1])],
                [float(center[0] + radius), float(center[1])],
            ]
        elif annotation.shape in {"obb", "obb_mirror", "obb_single", "line_expand"}:
            shape_type = "oriented_rectangle"
            labelme_points = [
                [float(x_pos), float(y_pos)] for x_pos, y_pos in points[:4]
            ]
        shapes.append(
            {
                "label": label,
                "points": labelme_points,
                "group_id": None,
                "description": "",
                "shape_type": shape_type,
                "flags": {},
                "mask": None,
            }
        )

    payload = {
        "version": "5.5.0",
        "flags": {},
        "shapes": shapes,
        "imagePath": image_path.name,
        "imageData": None,
        "imageHeight": int(height),
        "imageWidth": int(width),
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def save_editable_annotations(
    image_size: tuple[int, int],
    label_path: Path,
    annotations: list[EditableAnnotation],
    output_mode: str,
) -> None:
    width, height = image_size
    label_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for annotation in annotations:
        if output_mode == "obb":
            values: list[float] = []
            points = annotation.points[:4]
            if annotation.shape == "polygon" or len(annotation.points) != 4:
                left, top, right, bottom = _detect_points_to_rect(annotation.points)
                points = [(left, top), (right, top), (right, bottom), (left, bottom)]
            for x_pos, y_pos in points:
                values.extend(
                    [
                        max(0.0, min(1.0, x_pos / width)),
                        max(0.0, min(1.0, y_pos / height)),
                    ]
                )
            lines.append(
                f"{annotation.class_id} "
                + " ".join(f"{value:.6f}" for value in values)
            )
        else:
            x1, y1, x2, y2 = _detect_points_to_rect(annotation.points)
            x1 = max(0.0, min(float(width), x1))
            x2 = max(0.0, min(float(width), x2))
            y1 = max(0.0, min(float(height), y1))
            y2 = max(0.0, min(float(height), y2))
            box_w = abs(x2 - x1)
            box_h = abs(y2 - y1)
            if box_w < 1 or box_h < 1:
                continue
            cx = (min(x1, x2) + box_w / 2) / width
            cy = (min(y1, y2) + box_h / 2) / height
            lines.append(
                f"{annotation.class_id} {cx:.6f} {cy:.6f} "
                f"{box_w / width:.6f} {box_h / height:.6f}"
            )
    if lines:
        label_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    elif label_path.exists():
        label_path.write_text("", encoding="utf-8")


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
        self.line_expand_enabled = False
        self.line_expand_pixels = 10
        self.changed_callback = None
        self.selection_callback = None

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
        self.move_anchor = None
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
        self.move_anchor = None
        self.update()

    def set_line_expand_config(self, enabled: bool, pixels: int) -> None:
        self.line_expand_enabled = bool(enabled)
        self.line_expand_pixels = max(1, int(pixels))

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
            )
        if self.drag_start and self.drag_current:
            preview = self._make_annotation(self.drag_start, self.drag_current)
            if preview:
                self._draw_annotation(painter, preview, selected=True, dashed=True)
        elif self.obb_first and self.obb_second and self.drag_current:
            preview = self._make_obb_annotation(
                self.obb_first, self.obb_second, self.drag_current
            )
            if preview:
                self._draw_annotation(painter, preview, selected=True, dashed=True)
        elif self.obb_first and self.preview_line_end:
            painter.setPen(QPen(QColor("#26394D"), 1))
            painter.drawLine(self._image_to_widget(self.obb_first), self._image_to_widget(self.preview_line_end))
        if self.polygon_points:
            preview_points = [self._image_to_widget(point) for point in self.polygon_points]
            painter.setPen(QPen(QColor("#26394D"), 1))
            for start, end in zip(preview_points, preview_points[1:]):
                painter.drawLine(start, end)
            if self.preview_line_end is not None:
                painter.drawLine(preview_points[-1], self._image_to_widget(self.preview_line_end))

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
            if self.obb_first is None:
                self.obb_first = image_point
                self.obb_second = None
                self.preview_line_end = image_point
            elif self.obb_second is None:
                self.obb_second = image_point
                self.drag_current = image_point
                self.preview_line_end = None
            else:
                annotation = self._make_obb_annotation(
                    self.obb_first, self.obb_second, image_point
                )
                if annotation is not None:
                    self.annotations.append(annotation)
                    self.selected_index = len(self.annotations) - 1
                    self._emit_changed()
                    self._emit_selection()
                self.obb_first = None
                self.obb_second = None
                self.drag_current = None
                self.preview_line_end = None
            self.update()
            return
        if self.draw_shape == "circle":
            if self.drag_start is None:
                self.drag_start = image_point
                self.drag_current = image_point
            else:
                annotation = self._make_annotation(self.drag_start, image_point)
                if annotation is not None:
                    self.annotations.append(annotation)
                    self.selected_index = len(self.annotations) - 1
                    self._emit_changed()
                    self._emit_selection()
                self.drag_start = None
                self.drag_current = None
            self.update()
            return
        if self.draw_shape == "polygon":
            if self.polygon_points and len(self.polygon_points) >= 3:
                first_x, first_y = self.polygon_points[0]
                dx = image_point[0] - first_x
                dy = image_point[1] - first_y
                if dx * dx + dy * dy <= max(36.0, self._handle_radius() ** 2 * 4):
                    annotation = EditableAnnotation(self.current_class_id, "polygon", list(self.polygon_points))
                    self.annotations.append(annotation)
                    self.selected_index = len(self.annotations) - 1
                    self.polygon_points = []
                    self.preview_line_end = None
                    self._emit_changed()
                    self._emit_selection()
                    self.update()
                    return
            self.polygon_points.append(image_point)
            self.preview_line_end = image_point
            self.update()
            return
        self.drag_start = image_point
        self.drag_current = image_point

    def mouseMoveEvent(self, event):  # noqa: N802 - Qt API name
        image_point = self._widget_to_image(event.position(), clamp=True)
        if self.draw_shape == "select":
            self._update_hover_state(image_point)
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
        if self.draw_shape in {"obb_mirror", "obb_single", "line_expand", "polygon", "circle"}:
            return
        if event.button() != Qt.MouseButton.LeftButton or self.drag_start is None:
            return
        if self.draw_shape == "circle":
            return
        image_point = self._widget_to_image(event.position())
        if image_point is not None:
            annotation = self._make_annotation(self.drag_start, image_point)
            if annotation is not None:
                self.annotations.append(annotation)
                self.selected_index = len(self.annotations) - 1
                self._emit_changed()
                self._emit_selection()
        self.drag_start = None
        self.drag_current = None
        self.update()

    def leaveEvent(self, event):  # noqa: N802 - Qt API name
        super().leaveEvent(event)
        self.hovered_index = -1
        self.hovered_handle = None
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
        width_point: tuple[float, float],
    ) -> EditableAnnotation | None:
        x1, y1 = start
        x2, y2 = end
        wx, wy = width_point
        dx = x2 - x1
        dy = y2 - y1
        length = (dx * dx + dy * dy) ** 0.5
        if length < 3:
            return None
        nx = -dy / length
        ny = dx / length
        raw_distance = (wx - x1) * nx + (wy - y1) * ny
        distance = abs(raw_distance)
        if distance < 3:
            return None
        if self.draw_shape == "line_expand":
            distance = float(self.line_expand_pixels)
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
    ) -> None:
        color = _class_color(annotation.class_id)
        pen = QPen(color, 2 if selected else 1)
        if dashed:
            pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        widget_points = [self._image_to_widget(point) for point in annotation.points]
        if selected and hovered and not dashed:
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
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def _cancel_current_drawing(self) -> bool:
        if self.drag_start is not None or self.obb_first is not None or self.polygon_points:
            self.drag_start = None
            self.drag_current = None
            self.obb_first = None
            self.obb_second = None
            self.preview_line_end = None
            self.polygon_points = []
            self.active_handle = None
            self.move_anchor = None
            return True
        if self.draw_shape != "select":
            self.set_draw_shape("select")
            return True
        return False

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
            self.drag_start is not None or self.obb_first is not None or self.active_handle is not None or self.move_anchor is not None
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
            self.drag_start = None
            self.drag_current = None
            self.obb_first = None
            self.obb_second = None
            self.active_handle = None
            self.move_anchor = None
            self.update()
        elif selected in class_actions and 0 <= self.selected_index < len(self.annotations):
            self.annotations[self.selected_index].class_id = class_actions[selected]
            self._emit_changed()
            self.update()
        elif selected in shape_actions:
            self.set_draw_shape(shape_actions[selected])


class AnnotationSettingsDialog(QDialog):
    def __init__(
        self,
        enabled: bool,
        pixels: int,
        auto_save: bool,
        auto_convert_yolo: bool,
        yolo_dir: str,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("更多设置")
        self.resize(420, 320)
        layout = QVBoxLayout(self)
        self.auto_save_check = QCheckBox("自动保存 Labelme JSON")
        self.auto_save_check.setChecked(bool(auto_save))
        layout.addWidget(self.auto_save_check)
        self.auto_convert_check = QCheckBox("自动转换为 YOLO 格式")
        self.auto_convert_check.setChecked(bool(auto_convert_yolo))
        layout.addWidget(self.auto_convert_check)
        layout.addWidget(QLabel("YOLO 标注文件夹"))
        yolo_row = QHBoxLayout()
        self.yolo_dir_edit = QLineEdit(yolo_dir)
        yolo_row.addWidget(self.yolo_dir_edit, 1)
        choose_btn = QPushButton("选择")
        choose_btn.clicked.connect(self.choose_yolo_dir)
        yolo_row.addWidget(choose_btn)
        layout.addLayout(yolo_row)
        self.enable_combo = QComboBox()
        self.enable_combo.addItems(["关闭直线标注", "开启直线标注"])
        self.enable_combo.setCurrentIndex(1 if enabled else 0)
        layout.addWidget(QLabel("直线标注"))
        layout.addWidget(self.enable_combo)
        self.pixel_spin = QSpinBox()
        self.pixel_spin.setRange(1, 200)
        self.pixel_spin.setValue(max(1, int(pixels)))
        layout.addWidget(QLabel("直线扩展像素"))
        layout.addWidget(self.pixel_spin)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def choose_yolo_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "选择 YOLO 标注文件夹", self.yolo_dir_edit.text().strip()
        )
        if directory:
            self.yolo_dir_edit.setText(directory)

    def values(self) -> tuple[bool, int, bool, bool, str]:
        return (
            self.enable_combo.currentIndex() == 1,
            int(self.pixel_spin.value()),
            self.auto_save_check.isChecked(),
            self.auto_convert_check.isChecked(),
            self.yolo_dir_edit.text().strip(),
        )


class DrawShapeDialog(QDialog):
    def __init__(self, line_expand_enabled: bool, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择标注类型")
        self.resize(220, 330 if line_expand_enabled else 286)
        self.selected_shape = "rect"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        title_label = QLabel("请选择要绘制的标注类型")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        options = [
            ("矩形框", "rect"),
            ("有向矩形", "obb_single"),
            ("镜像有向矩形", "obb_mirror"),
            ("多边形", "polygon"),
            ("圆形", "circle"),
        ]
        if line_expand_enabled:
            options.append(("直线扩展", "line_expand"))
        self._options = options

        list_frame = QFrame()
        list_frame.setObjectName("drawShapeList")
        list_layout = QVBoxLayout(list_frame)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(0)
        for index, (text, value) in enumerate(options):
            button = QPushButton(text)
            button.setMinimumHeight(44)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            if len(options) == 1:
                object_name = "drawShapeOptionSingle"
            elif index == 0:
                object_name = "drawShapeOptionFirst"
            elif index == len(options) - 1:
                object_name = "drawShapeOptionLast"
            else:
                object_name = "drawShapeOption"
            button.setObjectName(object_name)
            button.clicked.connect(lambda _checked=False, shape=value: self.choose_shape(shape))
            list_layout.addWidget(button)
        layout.addWidget(list_frame)
        layout.addStretch(1)
        self.setStyleSheet(
            """
            QFrame#drawShapeList {
                background: #FFFFFF;
                border: 1px solid #D9E3EC;
                border-radius: 10px;
            }
            QPushButton#drawShapeOptionSingle,
            QPushButton#drawShapeOptionFirst,
            QPushButton#drawShapeOption,
            QPushButton#drawShapeOptionLast {
                background: #FFFFFF;
                color: #14233A;
                border: 0;
                border-radius: 0;
                padding: 10px 14px;
                text-align: center;
                font-size: 15px;
            }
            QPushButton#drawShapeOptionSingle {
                border-radius: 10px;
            }
            QPushButton#drawShapeOptionFirst {
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                border-bottom: 1px solid #E6EDF4;
            }
            QPushButton#drawShapeOption {
                border-bottom: 1px solid #E6EDF4;
            }
            QPushButton#drawShapeOptionLast {
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
            QPushButton#drawShapeOptionSingle:hover,
            QPushButton#drawShapeOptionFirst:hover,
            QPushButton#drawShapeOption:hover,
            QPushButton#drawShapeOptionLast:hover {
                background: #F5F8FB;
            }
            """
        )

    def choose_shape(self, shape: str) -> None:
        self.selected_shape = shape
        self.accept()


class CustomAiImageSelectionDialog(QDialog):
    def __init__(
        self,
        image_items: list[Path],
        selected_images: list[Path] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("自定义图片列表")
        self.resize(360, 560)
        self.setMinimumSize(220, 240)
        self.image_items = list(image_items)
        self.selected_paths = {
            Path(path).resolve() for path in (selected_images or [])
        }
        self.visible_paths: list[Path] = []
        self.checkboxes: dict[Path, QCheckBox] = {}
        self._drag_select_active = False
        self._drag_select_state = False
        self._drag_last_row = -1
        self._drag_viewport_pos = QPoint()
        self._auto_scroll_direction = 0
        self._auto_scroll_step = 0
        self._auto_scroll_timer = QTimer(self)
        self._auto_scroll_timer.setInterval(30)
        self._auto_scroll_timer.timeout.connect(self._perform_auto_scroll_step)

        layout = QVBoxLayout(self)
        self.listing = QListWidget()
        self.listing.itemClicked.connect(self.toggle_item_from_row)
        self.listing.viewport().installEventFilter(self)
        layout.addWidget(self.listing, 1)

        bulk_row = QHBoxLayout()
        bulk_row.setContentsMargins(0, 0, 0, 0)
        bulk_row.setSpacing(8)
        select_all_btn = QPushButton("全选")
        select_all_btn.clicked.connect(self.select_all_visible)
        bulk_row.addWidget(select_all_btn)
        invert_btn = QPushButton("反选")
        invert_btn.clicked.connect(self.invert_visible_selection)
        bulk_row.addWidget(invert_btn)
        clear_btn = QPushButton("全不选")
        clear_btn.clicked.connect(self.clear_visible_selection)
        bulk_row.addWidget(clear_btn)
        bulk_row.addStretch(1)
        layout.addLayout(bulk_row)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索文件名")
        self.search_edit.textChanged.connect(self.refresh_items)
        layout.addWidget(self.search_edit)

        footer_row = QHBoxLayout()
        footer_row.setContentsMargins(0, 0, 0, 0)
        footer_row.setSpacing(8)
        self.selected_count_label = QLabel("")
        self.selected_count_label.setObjectName("fieldLabel")
        footer_row.addWidget(self.selected_count_label)
        footer_row.addStretch(1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        footer_row.addWidget(buttons)
        layout.addLayout(footer_row)
        self.refresh_items()

    def _set_path_selected(self, path: Path, checked: bool) -> None:
        resolved = Path(path).resolve()
        if checked:
            self.selected_paths.add(resolved)
        else:
            self.selected_paths.discard(resolved)
        self._refresh_selected_count_label()

    def _refresh_selected_count_label(self) -> None:
        if hasattr(self, "selected_count_label"):
            self.selected_count_label.setText(f"已选择 {len(self.selected_paths)} 张图片")

    def refresh_items(self, text: str = "") -> None:
        needle = text.strip().lower()
        self.visible_paths = [
            path
            for path in self.image_items
            if not needle or needle in path.name.lower()
        ]
        self.checkboxes = {}
        self.listing.clear()
        for path in self.visible_paths:
            resolved = Path(path).resolve()
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, str(resolved))
            checkbox = QCheckBox(path.name)
            checkbox.setChecked(resolved in self.selected_paths)
            checkbox.toggled.connect(
                lambda checked, current_path=path: self._set_path_selected(
                    current_path, checked
                )
            )
            self.listing.addItem(item)
            self.listing.setItemWidget(item, checkbox)
            item.setSizeHint(checkbox.sizeHint())
            self.checkboxes[resolved] = checkbox
        self._refresh_selected_count_label()

    def toggle_item_from_row(self, item: QListWidgetItem) -> None:
        raw_path = str(item.data(Qt.ItemDataRole.UserRole) or "")
        if not raw_path:
            return
        checkbox = self.checkboxes.get(Path(raw_path).resolve())
        if checkbox is not None:
            checkbox.toggle()

    def _set_item_checked(self, item: QListWidgetItem, checked: bool) -> None:
        raw_path = str(item.data(Qt.ItemDataRole.UserRole) or "")
        if not raw_path:
            return
        resolved = Path(raw_path).resolve()
        checkbox = self.checkboxes.get(resolved)
        if checkbox is not None:
            checkbox.setChecked(checked)
        else:
            self._set_path_selected(Path(raw_path), checked)

    def _item_from_viewport_pos(self, pos) -> QListWidgetItem | None:
        item = self.listing.itemAt(pos)
        return item if item is not None else None

    def _clamped_viewport_pos(self, pos: QPoint) -> QPoint:
        viewport = self.listing.viewport()
        x_pos = min(max(0, pos.x()), max(0, viewport.width() - 1))
        y_pos = min(max(0, pos.y()), max(0, viewport.height() - 1))
        return QPoint(x_pos, y_pos)

    def _row_for_item(self, item: QListWidgetItem | None) -> int:
        if item is None:
            return -1
        return self.listing.row(item)

    def _apply_drag_selection_to_row(self, row: int) -> None:
        if row < 0:
            return
        if self._drag_last_row < 0:
            start_row = row
            end_row = row
        else:
            start_row = min(self._drag_last_row, row)
            end_row = max(self._drag_last_row, row)
        for current_row in range(start_row, end_row + 1):
            item = self.listing.item(current_row)
            if item is not None:
                self._set_item_checked(item, self._drag_select_state)
        self._drag_last_row = row

    def _update_auto_scroll(self, pos: QPoint) -> None:
        viewport = self.listing.viewport()
        edge_threshold = 36
        direction = 0
        step = 0
        if pos.y() < edge_threshold:
            depth = edge_threshold - pos.y()
            ratio = min(1.0, depth / edge_threshold)
            direction = -1
            step = max(1, int(1 + ratio * 7))
        elif pos.y() > max(0, viewport.height() - edge_threshold):
            depth = pos.y() - max(0, viewport.height() - edge_threshold)
            ratio = min(1.0, depth / edge_threshold)
            direction = 1
            step = max(1, int(1 + ratio * 7))

        self._auto_scroll_direction = direction
        self._auto_scroll_step = step
        if direction == 0:
            self._auto_scroll_timer.stop()
        elif not self._auto_scroll_timer.isActive():
            self._auto_scroll_timer.start()

    def _stop_drag_auto_scroll(self) -> None:
        self._auto_scroll_timer.stop()
        self._auto_scroll_direction = 0
        self._auto_scroll_step = 0

    def _apply_drag_selection_from_pos(self, pos: QPoint) -> None:
        self._drag_viewport_pos = QPoint(pos)
        item = self._item_from_viewport_pos(self._clamped_viewport_pos(pos))
        if item is not None:
            self._apply_drag_selection_to_row(self._row_for_item(item))
        self._update_auto_scroll(pos)

    def _perform_auto_scroll_step(self) -> None:
        if not self._drag_select_active or self._auto_scroll_direction == 0:
            self._stop_drag_auto_scroll()
            return
        scrollbar = self.listing.verticalScrollBar()
        previous_value = scrollbar.value()
        scrollbar.setValue(
            previous_value + self._auto_scroll_direction * self._auto_scroll_step
        )
        if scrollbar.value() == previous_value:
            self._stop_drag_auto_scroll()
            return
        item = self._item_from_viewport_pos(
            self._clamped_viewport_pos(self._drag_viewport_pos)
        )
        if item is not None:
            self._apply_drag_selection_to_row(self._row_for_item(item))

    def eventFilter(self, watched, event):
        if watched is self.listing.viewport():
            if event.type() == QEvent.Type.MouseButtonPress:
                pos = event.position().toPoint()
                item = self._item_from_viewport_pos(self._clamped_viewport_pos(pos))
                if item is not None and event.button() == Qt.MouseButton.LeftButton:
                    raw_path = str(item.data(Qt.ItemDataRole.UserRole) or "")
                    checkbox = self.checkboxes.get(Path(raw_path).resolve()) if raw_path else None
                    if checkbox is not None:
                        self._drag_select_active = True
                        self._drag_select_state = not checkbox.isChecked()
                        self._drag_last_row = -1
                        self._apply_drag_selection_from_pos(pos)
                        return True
            elif event.type() == QEvent.Type.MouseMove and self._drag_select_active:
                self._apply_drag_selection_from_pos(event.position().toPoint())
                return True
            elif event.type() == QEvent.Type.MouseButtonRelease and self._drag_select_active:
                self._drag_select_active = False
                self._drag_last_row = -1
                self._stop_drag_auto_scroll()
                return True
        return super().eventFilter(watched, event)

    def _apply_visible_selection(self, resolver) -> None:
        for path in self.visible_paths:
            resolved = Path(path).resolve()
            checkbox = self.checkboxes.get(resolved)
            checked = resolver(resolved)
            if checkbox is not None:
                checkbox.setChecked(checked)
            else:
                self._set_path_selected(path, checked)

    def select_all_visible(self) -> None:
        self._apply_visible_selection(lambda _path: True)

    def invert_visible_selection(self) -> None:
        self._apply_visible_selection(
            lambda current_path: current_path not in self.selected_paths
        )

    def clear_visible_selection(self) -> None:
        self._apply_visible_selection(lambda _path: False)

    def selected_image_paths(self) -> list[Path]:
        return [
            path
            for path in self.image_items
            if Path(path).resolve() in self.selected_paths
        ]


class AiPrelabelDialog(QDialog):
    def __init__(self, page: "AnnotationPage", parent=None):
        super().__init__(parent or page)
        self.page = page
        self.stop_event = threading.Event()
        self.ai_worker: AnnotationAiWorker | None = None
        self.labels_worker: ModelLabelsWorker | None = None
        self._model_display_paths: dict[str, Path] = {}
        self.model_labels: list[str] = []
        self.mapping_combos: list[QComboBox] = []
        self.backups: dict[Path, tuple[str | None, str | None]] = {}
        self.custom_selected_images: list[Path] = []
        self.original_class_names = list(page.class_names())
        self._load_saved_preferences()
        self.setWindowTitle("AI 智能预标注")
        self.resize(700, 620)
        self.setMinimumSize(650, 520)
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 12)
        root.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(10)

        model_card = QFrame()
        model_card.setObjectName("card")
        model_layout = QVBoxLayout(model_card)
        model_layout.setContentsMargins(12, 10, 12, 10)
        model_layout.setSpacing(8)
        title = QLabel("模型与参数")
        title.setObjectName("sectionTitle")
        model_layout.addWidget(title)

        model_row = QHBoxLayout()
        model_row.setContentsMargins(0, 0, 0, 0)
        model_row.setSpacing(8)
        model_label = QLabel("模型文件:")
        model_label.setObjectName("annotationPathLabel")
        model_row.addWidget(model_label)
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        preferred_model = self._preferred_model_text()
        self.refresh_model_choices(str(preferred_model) if preferred_model else "")
        model_row.addWidget(self.model_combo, 1)
        browse_btn = QPushButton("浏览")
        browse_btn.clicked.connect(self.choose_model)
        model_row.addWidget(browse_btn)
        model_layout.addLayout(model_row)

        threshold_row = QHBoxLayout()
        threshold_row.setContentsMargins(0, 0, 0, 0)
        threshold_row.setSpacing(8)
        conf_label = QLabel("置信度:")
        conf_label.setObjectName("annotationPathLabel")
        threshold_row.addWidget(conf_label)
        self.conf_spin = QDoubleSpinBox()
        self.conf_spin.setRange(0.0, 1.0)
        self.conf_spin.setSingleStep(0.05)
        self.conf_spin.setDecimals(2)
        self.conf_spin.setValue(self.saved_confidence)
        threshold_row.addWidget(self.conf_spin)
        iou_label = QLabel("IoU:")
        iou_label.setObjectName("annotationPathLabel")
        threshold_row.addSpacing(12)
        threshold_row.addWidget(iou_label)
        self.iou_spin = QDoubleSpinBox()
        self.iou_spin.setRange(0.0, 1.0)
        self.iou_spin.setSingleStep(0.05)
        self.iou_spin.setDecimals(2)
        self.iou_spin.setValue(self.saved_iou)
        threshold_row.addWidget(self.iou_spin)
        threshold_row.addStretch(1)
        model_layout.addLayout(threshold_row)
        top_row.addWidget(model_card, 3)

        options_card = QFrame()
        options_card.setObjectName("card")
        options_layout = QVBoxLayout(options_card)
        options_layout.setContentsMargins(12, 10, 12, 10)
        options_layout.setSpacing(8)
        options_title = QLabel("范围与模式")
        options_title.setObjectName("sectionTitle")
        options_layout.addWidget(options_title)

        range_row = QHBoxLayout()
        range_row.setContentsMargins(0, 0, 0, 0)
        range_row.setSpacing(8)
        range_label = QLabel("标注范围:")
        range_label.setObjectName("annotationPathLabel")
        range_row.addWidget(range_label)
        self.range_combo = QComboBox()
        self.range_combo.addItems(
            ["当前图片", "当前及以后图片", "全部未标注图片", "全部图片", "自定义图片"]
        )
        self.range_combo.currentTextChanged.connect(self.on_range_mode_changed)
        self.range_combo.setCurrentText(self.saved_range_mode)
        range_row.addWidget(self.range_combo, 1)
        self.range_count_label = QLabel("")
        self.range_count_label.setObjectName("fieldLabel")
        range_row.addWidget(self.range_count_label)
        self.range_list_btn = QPushButton("图片列表")
        self.range_list_btn.setObjectName("softButton")
        self.range_list_btn.clicked.connect(self.open_custom_image_list)
        self.range_list_btn.hide()
        range_row.addWidget(self.range_list_btn)
        options_layout.addLayout(range_row)

        process_row = QHBoxLayout()
        process_row.setContentsMargins(0, 0, 0, 0)
        process_row.setSpacing(8)
        process_label = QLabel("处理模式:")
        process_label.setObjectName("annotationPathLabel")
        process_row.addWidget(process_label)
        self.append_radio = QRadioButton("追加")
        self.append_radio.setToolTip("保留原有标注，并追加 AI 识别出的新标注。")
        self.replace_radio = QRadioButton("替换")
        self.replace_radio.setToolTip("清除原有标注，仅保留本次 AI 预标注结果。")
        self.append_radio.setChecked(self.saved_process_mode != "替换")
        self.replace_radio.setChecked(self.saved_process_mode == "替换")
        self.process_group = QButtonGroup(self)
        self.process_group.addButton(self.append_radio)
        self.process_group.addButton(self.replace_radio)
        process_row.addWidget(self.append_radio)
        process_row.addWidget(self.replace_radio)
        process_row.addStretch(1)
        options_layout.addLayout(process_row)
        top_row.addWidget(options_card, 2)
        root.addLayout(top_row)

        mapping_card = QFrame()
        mapping_card.setObjectName("card")
        mapping_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        mapping_layout = QVBoxLayout(mapping_card)
        mapping_layout.setContentsMargins(12, 10, 12, 10)
        mapping_layout.setSpacing(6)
        mapping_header = QHBoxLayout()
        mapping_header.setContentsMargins(0, 0, 0, 0)
        mapping_title = QLabel("类别映射")
        mapping_title.setObjectName("sectionTitle")
        mapping_header.addWidget(mapping_title)
        mapping_header.addStretch(1)
        self.mapping_summary = QLabel("等待加载模型类别")
        self.mapping_summary.setObjectName("fieldLabel")
        mapping_header.addWidget(self.mapping_summary)
        mapping_layout.addLayout(mapping_header)
        self.mapping_table = QTableWidget(0, 4)
        self.mapping_table.setHorizontalHeaderLabels(["#", "模型类别", "标注类别", "状态"])
        self.mapping_table.verticalHeader().setVisible(False)
        self.mapping_table.verticalHeader().setDefaultSectionSize(38)
        self.mapping_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.mapping_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.mapping_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.mapping_table.setMinimumHeight(140)
        self.mapping_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.mapping_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.mapping_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.mapping_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.mapping_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.mapping_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        mapping_layout.addWidget(self.mapping_table, 1)
        root.addWidget(mapping_card, 4)

        progress_card = QFrame()
        progress_card.setObjectName("card")
        progress_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        progress_layout = QVBoxLayout(progress_card)
        progress_layout.setContentsMargins(12, 10, 12, 10)
        progress_layout.setSpacing(6)
        progress_header = QHBoxLayout()
        progress_header.setContentsMargins(0, 0, 0, 0)
        progress_title = QLabel("运行进度")
        progress_title.setObjectName("sectionTitle")
        progress_header.addWidget(progress_title)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_header.addWidget(self.progress_bar, 1)
        progress_layout.addLayout(progress_header)
        self.progress_log = QTextEdit()
        self.page.prepare_readonly_text(self.progress_log)
        self.progress_log.setMinimumHeight(44)
        self.progress_log.setMaximumHeight(88)
        progress_layout.addWidget(self.progress_log, 1)
        root.addWidget(progress_card)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 2, 0, 0)
        button_row.setSpacing(10)
        button_row.addStretch(1)
        self.start_btn = QPushButton("开始预标注")
        self.start_btn.clicked.connect(self.start_ai_labeling)
        button_row.addWidget(self.start_btn)
        self.stop_btn = QPushButton("停止标注")
        self.stop_btn.setObjectName("softButton")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_ai_labeling)
        button_row.addWidget(self.stop_btn)
        self.undo_btn = QPushButton("删除AI标注")
        self.undo_btn.setEnabled(False)
        self.undo_btn.clicked.connect(self.undo_ai_changes)
        button_row.addWidget(self.undo_btn)
        back_btn = QPushButton("返回标注")
        back_btn.setObjectName("softButton")
        back_btn.clicked.connect(self.accept)
        button_row.addWidget(back_btn)
        root.addLayout(button_row)

        self.model_combo.currentTextChanged.connect(self.reload_model_labels)
        self.reload_model_labels()
        self.on_range_mode_changed(self.current_range_mode())

    def _ai_prelabel_settings(self) -> dict:
        annotation_settings = self.page.app.settings.setdefault("annotation", {})
        return annotation_settings.setdefault("ai_prelabel", {})

    def _load_saved_preferences(self) -> None:
        saved = self._ai_prelabel_settings()
        self.saved_model_path = str(saved.get("model_path", "")).strip()
        self.saved_confidence = float(saved.get("confidence", 0.50) or 0.50)
        self.saved_iou = float(saved.get("iou", 0.45) or 0.45)
        self.saved_range_mode = str(saved.get("range_mode", "当前图片") or "当前图片")
        if self.saved_range_mode not in {
            "当前图片", "当前及以后图片", "全部未标注图片", "全部图片", "自定义图片"
        }:
            self.saved_range_mode = "当前图片"
        self.saved_process_mode = str(saved.get("process_mode", "追加") or "追加")
        if self.saved_process_mode not in {"追加", "替换"}:
            self.saved_process_mode = "追加"
        selected_images = saved.get("custom_selected_images", [])
        if not isinstance(selected_images, list):
            selected_images = []
        project_root = self.page.project_root()
        self.custom_selected_images = []
        for raw_path in selected_images:
            try:
                path = Path(str(raw_path).strip())
            except (TypeError, ValueError):
                continue
            resolved = path if path.is_absolute() else project_root / path
            self.custom_selected_images.append(resolved.resolve())

    def _preferred_model_text(self) -> str:
        if self.saved_model_path:
            return self.saved_model_path
        training_settings = self.page.app.settings.get("training", {})
        preferred_model = training_settings.get("pretrained", "") or training_settings.get("base_model", "")
        return str(preferred_model or "")

    def _save_preferences(self) -> None:
        settings = self._ai_prelabel_settings()
        settings["model_path"] = self.resolved_model_path() or self.model_combo.currentText().strip()
        settings["confidence"] = float(self.conf_spin.value())
        settings["iou"] = float(self.iou_spin.value())
        settings["range_mode"] = self.current_range_mode()
        settings["process_mode"] = self.current_process_mode()
        project_root = self.page.project_root().resolve()
        saved_paths: list[str] = []
        for path in self.custom_selected_images:
            resolved = Path(path).resolve()
            try:
                saved_paths.append(str(resolved.relative_to(project_root)))
            except ValueError:
                saved_paths.append(str(resolved))
        settings["custom_selected_images"] = saved_paths
        self.page.save_settings()

    def accept(self) -> None:
        self._save_preferences()
        super().accept()

    def reject(self) -> None:
        self._save_preferences()
        super().reject()

    def choose_model(self) -> None:
        models_dir = self.page.project_root() / "data" / "models"
        models_dir.mkdir(parents=True, exist_ok=True)
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择模型文件",
            str(models_dir),
            "PyTorch 模型 (*.pt);;所有文件 (*)",
        )
        if path:
            self.model_combo.setCurrentText(self.page.display_path(path))

    def refresh_model_choices(self, preferred_model: str = "") -> None:
        project_root = self.page.project_root()
        result_dir = Path(self.page.app.settings["paths"]["result_dir"])
        self._model_display_paths = {}
        display_names: list[str] = []
        seen: set[str] = set()

        for path in _find_models_full_paths(
            result_dir, show_last_training_models=False
        ):
            resolved_path = path.resolve()
            resolved_text = str(resolved_path)
            if resolved_text in seen:
                continue
            display_name = _simplified_model_path(str(resolved_path), project_root)
            self._model_display_paths[display_name] = resolved_path
            display_names.append(display_name)
            seen.add(resolved_text)

        for model_name in available_ai_models(project_root):
            resolved_text = resolve_ai_model_path(model_name, project_root)
            if resolved_text in seen:
                continue
            display_names.append(model_name)
            if resolved_text:
                self._model_display_paths[model_name] = Path(resolved_text)
                seen.add(resolved_text)

        selected_text = ""
        preferred_text = str(preferred_model or "").strip()
        if preferred_text:
            preferred_path = Path(resolve_ai_model_path(preferred_text, project_root))
            for display_name, resolved_path in self._model_display_paths.items():
                if resolved_path == preferred_path:
                    selected_text = display_name
                    break
            else:
                selected_text = preferred_path.name if preferred_path.name else preferred_text

        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        self.model_combo.addItems(display_names)
        if selected_text:
            self.model_combo.setCurrentText(selected_text)
        self.model_combo.blockSignals(False)

    def current_range_mode(self) -> str:
        return self.range_combo.currentText() or "当前图片"

    def current_process_mode(self) -> str:
        return "替换" if self.replace_radio.isChecked() else "追加"

    def resolved_target_images(self) -> list[Path]:
        return collect_ai_target_images(
            self.page.image_items,
            self.page.current_image_path,
            self.page.path_from_setting("annotations_dir"),
            self.page.path_from_setting("labels_dir"),
            self.current_range_mode(),
            current_index=self.page.current_index,
            selected_images=self.custom_selected_images,
        )

    def on_range_mode_changed(self, _text: str = "") -> None:
        is_custom = self.current_range_mode() == "自定义图片"
        self.range_count_label.setHidden(is_custom)
        self.range_list_btn.setHidden(not is_custom)
        self.range_list_btn.setText("列表")
        self.update_target_count()

    def open_custom_image_list(self) -> None:
        if not self.page.image_items:
            QMessageBox.information(self, "AI 预标注", "当前图片文件夹没有可选择的图片。")
            return
        dialog = CustomAiImageSelectionDialog(
            self.page.image_items,
            self.custom_selected_images,
            self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.custom_selected_images = dialog.selected_image_paths()
            self.update_target_count()

    def resolved_model_path(self) -> str:
        text = self.model_combo.currentText().strip()
        mapped = self._model_display_paths.get(text)
        if mapped is not None:
            return str(mapped)
        return resolve_ai_model_path(text, self.page.project_root())

    def reload_model_labels(self) -> None:
        model_path = self.resolved_model_path()
        self.mapping_summary.setText("正在加载模型类别...")
        self.mapping_table.setRowCount(0)
        if self.labels_worker is not None and self.labels_worker.isRunning():
            return
        if not model_path:
            self.mapping_summary.setText("未选择模型")
            return
        self.labels_worker = ModelLabelsWorker(model_path)
        self.labels_worker.finished_with_labels.connect(self.apply_model_labels)
        self.labels_worker.failed.connect(self.apply_model_labels_error)
        self.labels_worker.finished.connect(self._clear_labels_worker)
        self.labels_worker.start()

    def _clear_labels_worker(self) -> None:
        self.labels_worker = None

    def apply_model_labels(self, labels: list[str]) -> None:
        self.model_labels = list(labels)
        self.populate_mapping_table()

    def apply_model_labels_error(self, message: str) -> None:
        self.mapping_summary.setText(f"加载模型类别失败：{message}")

    def populate_mapping_table(self) -> None:
        names = self.page.class_names()
        self.mapping_combos = []
        self.mapping_table.setRowCount(len(self.model_labels))
        matched = 0
        for row, model_label in enumerate(self.model_labels):
            index_item = QTableWidgetItem(str(row))
            label_item = QTableWidgetItem(model_label)
            combo = QComboBox()
            combo.setMinimumHeight(28)
            combo.setStyleSheet("QComboBox { padding: 2px 6px; }")
            combo.addItem("-- 跳过 --", "")
            for name in names:
                combo.addItem(name, name)
            if model_label in names:
                combo.setCurrentText(model_label)
                matched += 1
            combo.currentTextChanged.connect(self.update_mapping_status)
            self.mapping_table.setItem(row, 0, index_item)
            self.mapping_table.setItem(row, 1, label_item)
            self.mapping_table.setCellWidget(row, 2, combo)
            status_item = QTableWidgetItem("")
            self.mapping_table.setItem(row, 3, status_item)
            self.mapping_combos.append(combo)
        self.update_mapping_status()
        skipped = len(self.model_labels) - matched
        self.mapping_summary.setText(
            f"共 {len(self.model_labels)} 个类别 | 已匹配: {matched} | 已跳过: {skipped} | 未处理: 0"
        )

    def update_mapping_status(self) -> None:
        matched = 0
        skipped = 0
        for row, combo in enumerate(self.mapping_combos):
            value = str(combo.currentData() or "")
            status = "未匹配"
            if value:
                matched += 1
                status = "已匹配"
            else:
                skipped += 1
                status = "跳过"
            item = self.mapping_table.item(row, 3)
            if item is not None:
                item.setText(status)
        if self.model_labels:
            self.mapping_summary.setText(
                f"共 {len(self.model_labels)} 个类别 | 已匹配: {matched} | 已跳过: {skipped} | 未处理: 0"
            )

    def update_target_count(self) -> None:
        targets = self.resolved_target_images()
        if self.current_range_mode() == "自定义图片":
            self.range_list_btn.setText("列表")
            self.range_list_btn.setToolTip(f"当前已选择 {len(targets)} 张图片")
            return
        self.range_count_label.setText(f"已选择 {len(targets)} 张图片")

    def append_log(self, text: str) -> None:
        self.progress_log.append(text)

    def _snapshot_targets(self, targets: list[Path]) -> None:
        self.backups = {}
        for image_path in targets:
            json_path = self.page.path_from_setting("annotations_dir") / f"{image_path.stem}.json"
            yolo_path = self.page.path_from_setting("labels_dir") / f"{image_path.stem}.txt"
            json_text = json_path.read_text(encoding="utf-8") if json_path.exists() else None
            yolo_text = yolo_path.read_text(encoding="utf-8") if yolo_path.exists() else None
            self.backups[image_path] = (json_text, yolo_text)

    def collect_mapping(self) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for row, combo in enumerate(self.mapping_combos):
            model_label = self.mapping_table.item(row, 1)
            if model_label is None:
                continue
            target = str(combo.currentData() or "")
            if target:
                mapping[model_label.text()] = target
        return mapping

    def start_ai_labeling(self) -> None:
        if self.ai_worker is not None and self.ai_worker.isRunning():
            return
        model_path = self.resolved_model_path()
        if not model_path:
            QMessageBox.warning(self, "AI 预标注", "请先选择模型文件。")
            return
        targets = self.resolved_target_images()
        if self.current_range_mode() == "自定义图片" and not targets:
            QMessageBox.information(self, "AI 预标注", "请先在图片列表中勾选至少一张图片。")
            return
        if not targets:
            QMessageBox.information(self, "AI 预标注", "当前没有可处理的图片。")
            return
        mapping = self.collect_mapping()
        if not mapping:
            QMessageBox.warning(self, "AI 预标注", "请至少匹配一个模型类别到标注类别。")
            return
        self._snapshot_targets(targets)
        self.original_class_names = list(self.page.class_names())
        self.progress_bar.setValue(0)
        self.progress_log.clear()
        self.append_log(f"已加载 {len(self.model_labels)} 个模型类别")
        self.stop_event.clear()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.undo_btn.setEnabled(False)
        worker_kwargs = {
            "image_items": list(self.page.image_items),
            "current_image": self.page.current_image_path,
            "annotations_dir": self.page.path_from_setting("annotations_dir"),
            "labels_dir": self.page.path_from_setting("labels_dir"),
            "model_path": model_path,
            "confidence": float(self.conf_spin.value()),
            "iou": float(self.iou_spin.value()),
            "imgsz": max(640, int(self.page.canvas.image_size[0] or 640)),
            "range_mode": self.current_range_mode(),
            "current_index": self.page.current_index,
            "selected_images": list(self.custom_selected_images),
            "process_mode": self.current_process_mode(),
            "class_mapping": mapping,
            "class_names": list(self.page.class_names()),
            "line_expand_pixels": self.page.app.settings.get("annotation", {}).get("line_expand_pixels", 10),
            "save_json_fn": save_labelme_annotations,
            "save_yolo_fn": save_editable_annotations,
            "output_mode": self.page.output_mode,
            "auto_convert_yolo": bool(self.page.app.settings.get("annotation", {}).get("auto_convert_yolo", False)),
        }
        self.ai_worker = AnnotationAiWorker(worker_kwargs, self.stop_event)
        self.ai_worker.progress_payload.connect(self.apply_progress)
        self.ai_worker.finished_with_result.connect(self.finish_ai_labeling)
        self.ai_worker.failed.connect(self.fail_ai_labeling)
        self.ai_worker.finished.connect(self._clear_ai_worker)
        self.ai_worker.start()

    def _clear_ai_worker(self) -> None:
        self.ai_worker = None

    def apply_progress(self, payload: dict) -> None:
        total = max(1, int(payload.get("total") or 1))
        index = int(payload.get("index") or 0)
        self.progress_bar.setValue(int(index * 100 / total))
        if payload.get("type") == "log":
            self.append_log(str(payload.get("message") or ""))
            return
        image_name = str(payload.get("image_name") or "")
        result_count = int(payload.get("result_count") or 0)
        self.append_log(f"{index}/{total} {image_name} -> 新增 {result_count} 个标注")

    def finish_ai_labeling(self, result) -> None:
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.undo_btn.setEnabled(bool(self.backups))
        self.progress_bar.setValue(100 if result.total else 0)
        self.append_log(f"完成：已处理 {result.processed}/{result.total} 张图片")
        self.page.refresh_file_list()
        if self.page.current_index >= 0:
            self.page.load_current()

    def fail_ai_labeling(self, message: str) -> None:
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.append_log(f"失败：{message}")
        QMessageBox.warning(self, "AI 预标注", message)

    def stop_ai_labeling(self) -> None:
        self.stop_event.set()
        self.stop_btn.setEnabled(False)
        self.append_log("已请求停止 AI 预标注")

    def undo_ai_changes(self) -> None:
        if not self.backups:
            return
        for image_path, (json_text, yolo_text) in self.backups.items():
            json_path = self.page.path_from_setting("annotations_dir") / f"{image_path.stem}.json"
            yolo_path = self.page.path_from_setting("labels_dir") / f"{image_path.stem}.txt"
            if json_text is None:
                if json_path.exists():
                    json_path.unlink()
            else:
                json_path.write_text(json_text, encoding="utf-8")
            if yolo_text is None:
                if yolo_path.exists():
                    yolo_path.unlink()
            else:
                yolo_path.write_text(yolo_text, encoding="utf-8")
        self.page.app.settings.setdefault("dataset", {})["class_names"] = list(self.original_class_names)
        self.page.save_settings()
        self.page._refresh_class_state()
        self.page.refresh_file_list()
        if self.page.current_index >= 0:
            self.page.load_current()
        self.append_log("已恢复本次 AI 预标注前的标注文件")
        self.undo_btn.setEnabled(False)


class ClassManagerDialog(QDialog):
    def __init__(self, class_names: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("管理类别")
        self.resize(360, 420)
        self.class_names = list(class_names)
        layout = QVBoxLayout(self)
        self.listing = QListWidget()
        layout.addWidget(self.listing, 1)
        row = QHBoxLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("类别名称")
        row.addWidget(self.name_edit, 1)
        add_btn = QPushButton("新增")
        add_btn.clicked.connect(self.add_class)
        row.addWidget(add_btn)
        rename_btn = QPushButton("重命名")
        rename_btn.clicked.connect(self.rename_class)
        row.addWidget(rename_btn)
        delete_btn = QPushButton("删除")
        delete_btn.clicked.connect(self.delete_class)
        row.addWidget(delete_btn)
        layout.addLayout(row)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.listing.currentRowChanged.connect(self.sync_name_edit)
        self.refresh()

    def sync_name_edit(self, row: int) -> None:
        if 0 <= row < len(self.class_names):
            self.name_edit.setText(self.class_names[row])

    def refresh(self) -> None:
        current = self.listing.currentRow()
        self.listing.clear()
        for index, name in enumerate(self.class_names):
            self.listing.addItem(f"{index} : {name}")
        if self.class_names:
            self.listing.setCurrentRow(min(max(current, 0), len(self.class_names) - 1))

    def add_class(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            return
        if name in self.class_names:
            QMessageBox.information(self, "管理类别", "类别名称已存在。")
            return
        self.class_names.append(name)
        self.refresh()
        self.listing.setCurrentRow(len(self.class_names) - 1)

    def rename_class(self) -> None:
        row = self.listing.currentRow()
        name = self.name_edit.text().strip()
        if row < 0 or not name:
            return
        if name in self.class_names and self.class_names[row] != name:
            QMessageBox.information(self, "管理类别", "类别名称已存在。")
            return
        self.class_names[row] = name
        self.refresh()
        self.listing.setCurrentRow(row)

    def delete_class(self) -> None:
        row = self.listing.currentRow()
        if row < 0:
            return
        if len(self.class_names) <= 1:
            QMessageBox.information(self, "管理类别", "至少保留一个类别。")
            return
        del self.class_names[row]
        self.refresh()


class AnnotationPage(BasePage):
    def __init__(self, app):
        super().__init__(app)
        self.image_items: list[Path] = []
        self.current_index = -1
        self.dirty = False
        self.current_json_path: Path | None = None
        self.current_yolo_path: Path | None = None
        self.current_image_path: Path | None = None
        self.output_mode = self.app.settings.get("task", {}).get("mode", "detect")
        self.current_class_id = 0

        root = QHBoxLayout(self)
        root.setContentsMargins(20, 14, 12, 12)
        root.setSpacing(8)
        root.addWidget(self._build_toolbar())
        root.addLayout(self._build_center(), 1)
        root.addWidget(self._build_right_panel())

        self._refresh_class_state()
        self._refresh_path_labels()
        delete_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Delete), self)
        delete_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        delete_shortcut.activated.connect(self.delete_selected)
        self._delete_shortcut = delete_shortcut
        self.scan_images(select_first=True)

    def _build_toolbar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("annotationSidebar")
        sidebar.setFixedWidth(178)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 22, 16, 18)
        layout.setSpacing(13)
        title = QLabel("数据标注")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("annotationTitle")
        self._set_help_target(
            title,
            "数据标注",
            "可通过右键菜单快速切换标注类型，默认保存和读取 Labelme 格式标注；可通过“更多设置”开启 YOLO 格式文件保存。",
        )
        layout.addWidget(title)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("annotationDivider")
        layout.addWidget(line)
        image_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)
        for text, slot, icon in [
            ("图片文件夹", self.choose_image_dir, image_icon),
            ("标签文件夹", self.choose_label_dir, image_icon),
            ("⬅️上一张(A)", self.prev_image, None),
            ("➡️下一张(D)", self.next_image, None),
            ("✎ 画标注框(W)", self.enable_draw_mode, None),
        ]:
            button = QPushButton(text)
            button.setObjectName("annotationToolButton")
            if text in {"⬅️上一张(A)", "➡️下一张(D)"}:
                button.setProperty("compactArrowButton", True)
                button.style().unpolish(button)
                button.style().polish(button)
            if icon is not None:
                button.setIcon(icon)
            button.clicked.connect(slot)
            layout.addWidget(button)
        ai_btn = QPushButton("🤖 AI预标注")
        ai_btn.setObjectName("annotationToolButton")
        ai_btn.clicked.connect(self.open_ai_prelabel_dialog)
        layout.addWidget(ai_btn)
        settings_btn = QPushButton("⚙ 更多设置")
        settings_btn.setObjectName("annotationToolButton")
        settings_btn.clicked.connect(self.open_annotation_settings)
        layout.addWidget(settings_btn)
        layout.addStretch(1)
        return sidebar

    def _build_center(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 2, 0, 0)
        layout.setSpacing(0)
        self.canvas = AnnotationCanvas()
        self.canvas.changed_callback = self.mark_dirty_and_save
        self.canvas.selection_callback = self.sync_selection
        layout.addWidget(self.canvas, 1)
        return layout

    def _build_right_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("annotationRightPanel")
        panel.setFixedWidth(230)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        mode_label = QLabel("任务类别：")
        mode_label.setObjectName("annotationPathLabel")
        layout.addWidget(mode_label)
        self.output_mode_combo = QComboBox()
        self.output_mode_combo.addItems(["detect", "obb"])
        self.output_mode_combo.setCurrentText(
            self.output_mode if self.output_mode in {"detect", "obb"} else "detect"
        )
        self.output_mode_combo.currentTextChanged.connect(self.change_output_mode)
        layout.addWidget(self.output_mode_combo)
        class_label = QLabel("标注类别：")
        class_label.setObjectName("annotationPathLabel")
        layout.addWidget(class_label)
        self.class_combo = QComboBox()
        self.class_combo.currentIndexChanged.connect(self.change_class)
        layout.addWidget(self.class_combo)
        manage_btn = QPushButton("🏷 管理类别")
        manage_btn.setObjectName("annotationPrimaryButton")
        manage_btn.clicked.connect(self.manage_classes)
        layout.addWidget(manage_btn)
        self.annotation_list = QListWidget()
        self.annotation_list.currentRowChanged.connect(self.select_annotation)
        layout.addWidget(self.annotation_list, 2)
        delete_btn = QPushButton("🗑 删除选中框(Del)")
        delete_btn.setObjectName("annotationPrimaryButton")
        delete_btn.clicked.connect(self.delete_selected)
        layout.addWidget(delete_btn)
        file_header = QHBoxLayout()
        file_header.setContentsMargins(0, 0, 0, 0)
        file_header.setSpacing(6)
        file_label = QLabel("图片列表：")
        file_label.setObjectName("annotationPathLabel")
        file_header.addWidget(file_label)
        file_header.addStretch(1)
        self.file_count_label = QLabel("0/0")
        self.file_count_label.setObjectName("annotationPathLabel")
        file_header.addWidget(self.file_count_label)
        layout.addLayout(file_header)
        self.file_list = QListWidget()
        self.file_list.currentRowChanged.connect(self.jump_to_file)
        layout.addWidget(self.file_list, 3)
        return panel

    def choose_image_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "选择图片文件夹", str(self.path_from_setting("images_dir"))
        )
        if not directory:
            return
        self.save_current()
        self.update_setting("paths", "images_dir", value=directory)
        self._refresh_path_labels()
        self.scan_images(select_first=True)

    def choose_label_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "选择 Labelme JSON 标签文件夹", str(self.path_from_setting("annotations_dir"))
        )
        if not directory:
            return
        self.save_current()
        self.update_setting("paths", "annotations_dir", value=directory)
        Path(directory).mkdir(parents=True, exist_ok=True)
        self._refresh_path_labels()
        self.load_current()

    def path_from_setting(self, key: str) -> Path:
        return Path(self.app.settings["paths"][key])

    def scan_images(self, *, select_first: bool) -> None:
        image_dir = self.path_from_setting("images_dir")
        self.image_items = (
            sorted(
                [
                    path
                    for path in image_dir.iterdir()
                    if path.is_file() and path.suffix.lower() in _IMAGE_SUFFIXES
                ],
                key=natural_sort_key,
            )
            if image_dir.exists()
            else []
        )
        if select_first and self.image_items:
            self.current_index = 0
        elif self.current_index >= len(self.image_items):
            self.current_index = 0 if self.image_items else -1
        self.refresh_file_list()
        if self.current_index >= 0:
            self.file_list.setCurrentRow(self.current_index)
            self.load_current()
        else:
            self._update_file_count_label()
            self.canvas.set_image(None, [], self.class_names())

    def prev_image(self) -> None:
        if not self.image_items:
            self.scan_images(select_first=True)
            return
        self.change_current_index((self.current_index - 1) % len(self.image_items))

    def next_image(self) -> None:
        if not self.image_items:
            self.scan_images(select_first=True)
            return
        self.change_current_index((self.current_index + 1) % len(self.image_items))

    def jump_to_file(self, row: int) -> None:
        if 0 <= row < len(self.image_items) and row != self.current_index:
            self.change_current_index(row)

    def change_current_index(self, index: int) -> None:
        self.save_current()
        self.current_index = index
        self.file_list.blockSignals(True)
        self.file_list.setCurrentRow(index)
        self.file_list.blockSignals(False)
        self._update_file_count_label()
        self.load_current()

    def load_current(self) -> None:
        if not (0 <= self.current_index < len(self.image_items)):
            return
        image_path = self.image_items[self.current_index]
        json_path = self.path_from_setting("annotations_dir") / f"{image_path.stem}.json"
        yolo_path = self.path_from_setting("labels_dir") / f"{image_path.stem}.txt"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        yolo_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with Image.open(image_path) as image:
                image_size = image.size
        except OSError as exc:
            QMessageBox.warning(self, "数据标注", f"无法打开图片：{exc}")
            return
        if json_path.exists():
            annotations, class_names = load_labelme_annotations(
                image_size,
                json_path,
                self.class_names(),
                self.app.settings.get("annotation", {}).get("line_expand_pixels", 10),
            )
            if class_names != self.class_names():
                self.app.settings.setdefault("dataset", {})["class_names"] = class_names
                self.save_settings()
                self._refresh_class_state()
        else:
            annotations = load_editable_annotations(image_size, yolo_path)
        self.current_json_path = json_path
        self.current_yolo_path = yolo_path
        self.current_image_path = image_path
        self.canvas.set_image(image_path, annotations, self.class_names())
        self.dirty = False
        self.refresh_annotation_list()
        self.refresh_file_list()

    def save_current(self, *, force: bool = False, save_json: bool = True) -> None:
        if not self.dirty and not force:
            return
        if self.current_json_path is None or self.current_image_path is None:
            return
        if self.canvas.image_size == (0, 0):
            return
        annotation_settings = self.app.settings.get("annotation", {})
        if save_json:
            save_labelme_annotations(
                self.canvas.image_size,
                self.current_json_path,
                self.current_image_path,
                self.canvas.annotations,
                self.class_names(),
            )
        if (
            annotation_settings.get("auto_convert_yolo", False) or force
        ) and self.current_yolo_path is not None:
            save_editable_annotations(
                self.canvas.image_size,
                self.current_yolo_path,
                self.canvas.annotations,
                self.output_mode,
            )
        if save_json:
            self.dirty = False

    def mark_dirty_and_save(self) -> None:
        self.dirty = True
        self.refresh_annotation_list()
        annotation_settings = self.app.settings.get("annotation", {})
        if annotation_settings.get("auto_save", True) or annotation_settings.get(
            "auto_convert_yolo", False
        ):
            self.save_current(save_json=annotation_settings.get("auto_save", True))

    def class_names(self) -> list[str]:
        names = [
            str(name).strip()
            for name in self.app.settings.get("dataset", {}).get("class_names", [])
            if str(name).strip()
        ]
        return names or ["weld"]

    def _refresh_class_state(self) -> None:
        names = self.class_names()
        self.current_class_id = min(max(self.current_class_id, 0), len(names) - 1)
        if hasattr(self, "class_combo"):
            self.class_combo.blockSignals(True)
            self.class_combo.clear()
            self.class_combo.addItems(names)
            self.class_combo.setCurrentIndex(self.current_class_id)
            self.class_combo.blockSignals(False)
        self.canvas.set_current_class(self.current_class_id) if hasattr(self, "canvas") else None
        self.canvas.set_class_names(names) if hasattr(self, "canvas") else None
        if hasattr(self, "canvas"):
            annotation_settings = self.app.settings.get("annotation", {})
            self.canvas.set_line_expand_config(
                annotation_settings.get("line_expand_enabled", False),
                annotation_settings.get("line_expand_pixels", 10),
            )

    def _refresh_path_labels(self) -> None:
        return None

    def change_class(self, index: int) -> None:
        self.current_class_id = max(0, index)
        self.canvas.set_current_class(self.current_class_id)

    def change_shape(self, text: str) -> None:
        mapping = {
            "矩形框": "rect",
            "圆形": "circle",
            "镜像有向矩形": "obb_mirror",
            "有向矩形": "obb_single",
            "多边形": "polygon",
            "直线扩展": "line_expand",
        }
        self.canvas.set_draw_shape(mapping.get(text, "rect"))

    def change_output_mode(self, text: str) -> None:
        mode = text if text in {"detect", "obb"} else "detect"
        self.output_mode = mode
        self.app.settings.setdefault("task", {})["mode"] = mode
        self.save_settings()
        if self.current_json_path is not None:
            self.dirty = True
            self.save_current()

    def enable_draw_mode(self) -> None:
        dialog = DrawShapeDialog(self.canvas.line_expand_enabled, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.canvas.set_draw_shape(dialog.selected_shape)
        self.canvas.setFocus()

    def open_ai_prelabel_dialog(self) -> None:
        dialog = AiPrelabelDialog(self, self)
        dialog.exec()

    def open_annotation_settings(self) -> None:
        current = self.app.settings.get("annotation", {})
        dialog = AnnotationSettingsDialog(
            current.get("line_expand_enabled", False),
            current.get("line_expand_pixels", 10),
            current.get("auto_save", True),
            current.get("auto_convert_yolo", False),
            str(self.path_from_setting("labels_dir")),
            self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        enabled, pixels, auto_save, auto_convert_yolo, yolo_dir = dialog.values()
        self.app.settings.setdefault("annotation", {})["line_expand_enabled"] = enabled
        self.app.settings["annotation"]["line_expand_pixels"] = pixels
        self.app.settings["annotation"]["auto_save"] = auto_save
        self.app.settings["annotation"]["auto_convert_yolo"] = auto_convert_yolo
        if yolo_dir:
            self.app.settings.setdefault("paths", {})["labels_dir"] = yolo_dir
            Path(yolo_dir).mkdir(parents=True, exist_ok=True)
        self.save_settings()
        self._refresh_class_state()
        if auto_save or auto_convert_yolo:
            self.save_current(force=True)

    def manage_classes(self) -> None:
        dialog = ClassManagerDialog(self.class_names(), self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.app.settings.setdefault("dataset", {})["class_names"] = dialog.class_names
        self.save_settings()
        self._refresh_class_state()
        self.canvas.set_class_names(dialog.class_names)
        self.refresh_annotation_list()

    def select_annotation(self, row: int) -> None:
        if row == self.canvas.selected_index:
            return
        self.canvas.selected_index = row
        self.canvas.update()

    def sync_selection(self, row: int) -> None:
        self.annotation_list.blockSignals(True)
        self.annotation_list.setCurrentRow(row)
        self.annotation_list.blockSignals(False)

    def refresh_annotation_list(self) -> None:
        names = self.class_names()
        self.annotation_list.blockSignals(True)
        self.annotation_list.clear()
        for index, annotation in enumerate(self.canvas.annotations):
            label = (
                names[annotation.class_id]
                if 0 <= annotation.class_id < len(names)
                else str(annotation.class_id)
            )
            shape_text = _SHAPE_LABELS.get(annotation.shape, annotation.shape)
            format_text = "obb" if annotation.shape in {"obb", "obb_mirror", "obb_single", "line_expand"} else "detect"
            item = QListWidgetItem(f"{index + 1}.{label}-{shape_text}（{format_text}）")
            self.annotation_list.addItem(item)
        self.annotation_list.setCurrentRow(self.canvas.selected_index)
        self.annotation_list.blockSignals(False)
        self.refresh_file_list()

    def _has_annotation_for_image(self, image_path: Path) -> bool:
        if self.current_image_path == image_path and bool(self.canvas.annotations):
            return True
        json_path = self.path_from_setting("annotations_dir") / f"{image_path.stem}.json"
        yolo_path = self.path_from_setting("labels_dir") / f"{image_path.stem}.txt"
        if json_path.exists():
            try:
                payload = json.loads(json_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return False
            return bool(payload.get("shapes"))
        if yolo_path.exists():
            try:
                return any(
                    line.strip()
                    for line in yolo_path.read_text(encoding="utf-8").splitlines()
                )
            except OSError:
                return False
        return False

    def _update_file_count_label(self) -> None:
        total = len(self.image_items)
        current = self.current_index + 1 if 0 <= self.current_index < total else 0
        if hasattr(self, "file_count_label"):
            self.file_count_label.setText(f"{current}/{total}")

    def refresh_file_list(self) -> None:
        if not hasattr(self, "file_list"):
            return
        self.file_list.blockSignals(True)
        self.file_list.clear()
        for path in self.image_items:
            checked = "☑︎" if self._has_annotation_for_image(path) else "☐"
            self.file_list.addItem(f"{checked} {path.name}")
        self.file_list.blockSignals(False)
        if 0 <= self.current_index < len(self.image_items):
            self.file_list.blockSignals(True)
            self.file_list.setCurrentRow(self.current_index)
            self.file_list.blockSignals(False)
        self._update_file_count_label()

    def delete_selected(self) -> None:
        if self.canvas.delete_selected():
            self.refresh_annotation_list()

    def keyPressEvent(self, event):  # noqa: N802 - Qt API name
        if event.key() == Qt.Key.Key_Delete:
            self.delete_selected()
            return
        if event.key() == Qt.Key.Key_A:
            self.prev_image()
            return
        if event.key() == Qt.Key.Key_D:
            self.next_image()
            return
        super().keyPressEvent(event)

    def on_show(self) -> None:
        self._refresh_path_labels()
        if not self.image_items:
            self.scan_images(select_first=True)
