from __future__ import annotations

from pathlib import Path

from PIL import Image
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QImage, QPixmap

from src.services.annotation import EditableAnnotation


def mirror_edit_points(
    points: list[tuple[float, float]],
) -> tuple[
    tuple[float, float],
    tuple[float, float],
    tuple[float, float],
    tuple[float, float],
] | None:
    if len(points) != 4:
        return None
    p0, p1, p2, p3 = points
    center_start = ((p0[0] + p3[0]) / 2, (p0[1] + p3[1]) / 2)
    center_end = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
    side_start = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
    side_end = ((p2[0] + p3[0]) / 2, (p2[1] + p3[1]) / 2)
    return center_start, center_end, side_start, side_end


def mirror_geometry(
    points: list[tuple[float, float]],
) -> tuple[tuple[float, float], tuple[float, float], float] | None:
    if len(points) != 4:
        return None
    p0, p1, p2, p3 = points
    center_start = ((p0[0] + p3[0]) / 2, (p0[1] + p3[1]) / 2)
    center_end = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
    dx = center_end[0] - center_start[0]
    dy = center_end[1] - center_start[1]
    length = (dx * dx + dy * dy) ** 0.5
    if length < 1e-6:
        return None
    nx = -dy / length
    ny = dx / length
    signed_half_width = (p0[0] - center_start[0]) * nx + (p0[1] - center_start[1]) * ny
    return center_start, center_end, signed_half_width


def rebuild_mirror_points(
    center_start: tuple[float, float],
    center_end: tuple[float, float],
    signed_half_width: float,
) -> list[tuple[float, float]] | None:
    dx = center_end[0] - center_start[0]
    dy = center_end[1] - center_start[1]
    length = (dx * dx + dy * dy) ** 0.5
    if length < 3 or abs(signed_half_width) < 3:
        return None
    nx = -dy / length
    ny = dx / length
    return [
        (center_start[0] + nx * signed_half_width, center_start[1] + ny * signed_half_width),
        (center_end[0] + nx * signed_half_width, center_end[1] + ny * signed_half_width),
        (center_end[0] - nx * signed_half_width, center_end[1] - ny * signed_half_width),
        (center_start[0] - nx * signed_half_width, center_start[1] - ny * signed_half_width),
    ]


def pixmap_from_path(path: Path) -> QPixmap:
    image = Image.open(path).convert("RGBA")
    data = image.tobytes("raw", "RGBA")
    qimage = QImage(data, image.width, image.height, image.width * 4, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimage.copy())


def image_rect(canvas) -> QRectF:
    if canvas.pixmap is None or canvas.pixmap.isNull():
        return QRectF()
    available = canvas.rect().adjusted(0, 0, 0, 0)
    scale = min(
        available.width() / canvas.pixmap.width(),
        available.height() / canvas.pixmap.height(),
    )
    width = canvas.pixmap.width() * scale
    height = canvas.pixmap.height() * scale
    left = available.left() + (available.width() - width) / 2
    top = available.top() + (available.height() - height) / 2
    return QRectF(left, top, width, height)


def image_to_widget(canvas, point: tuple[float, float]) -> QPointF:
    target = image_rect(canvas)
    width, height = canvas.image_size
    return QPointF(
        target.left() + point[0] / width * target.width(),
        target.top() + point[1] / height * target.height(),
    )


def widget_to_image(canvas, point: QPointF, clamp: bool = False) -> tuple[float, float] | None:
    target = image_rect(canvas)
    if not clamp and not target.contains(point):
        return None
    width, height = canvas.image_size
    x_widget = min(max(point.x(), target.left()), target.right())
    y_widget = min(max(point.y(), target.top()), target.bottom())
    x_pos = (x_widget - target.left()) / target.width() * width
    y_pos = (y_widget - target.top()) / target.height() * height
    return (
        max(0.0, min(float(width), x_pos)),
        max(0.0, min(float(height), y_pos)),
    )


def make_annotation(
    canvas,
    start: tuple[float, float],
    end: tuple[float, float],
) -> EditableAnnotation | None:
    x1, y1 = start
    x2, y2 = end
    if abs(x2 - x1) < 3 or abs(y2 - y1) < 3:
        return None
    left, right = sorted((x1, x2))
    top, bottom = sorted((y1, y2))
    if canvas.draw_shape == "circle":
        radius = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        if radius < 3:
            return None
        left = x1 - radius
        right = x1 + radius
        top = y1 - radius
        bottom = y1 + radius
        shape = "circle"
    elif canvas.draw_shape in {"obb_mirror", "obb_single", "line_expand"}:
        shape = canvas.draw_shape
    else:
        shape = "rect"
    points = [(left, top), (right, top), (right, bottom), (left, bottom)]
    return EditableAnnotation(
        canvas.current_class_id,
        shape,
        points,
        radius_point=(x2, y2) if shape == "circle" else None,
    )


def make_obb_annotation(
    canvas,
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
    if canvas.draw_shape == "line_expand":
        distance = float(canvas.line_expand_pixels)
        points = [
            (x1 + nx * distance, y1 + ny * distance),
            (x2 + nx * distance, y2 + ny * distance),
            (x2 - nx * distance, y2 - ny * distance),
            (x1 - nx * distance, y1 - ny * distance),
        ]
        return EditableAnnotation(canvas.current_class_id, "obb_mirror", points)
    if width_point is None:
        return None
    wx, wy = width_point
    raw_distance = (wx - x1) * nx + (wy - y1) * ny
    distance = abs(raw_distance)
    if distance < 3:
        return None
    if canvas.draw_shape == "obb_single":
        side = 1.0 if raw_distance >= 0 else -1.0
        points = [
            (x1, y1),
            (x2, y2),
            (x2 + nx * distance * side, y2 + ny * distance * side),
            (x1 + nx * distance * side, y1 + ny * distance * side),
        ]
        return EditableAnnotation(canvas.current_class_id, "obb_single", points)
    points = [
        (x1 + nx * distance, y1 + ny * distance),
        (x2 + nx * distance, y2 + ny * distance),
        (x2 - nx * distance, y2 - ny * distance),
        (x1 - nx * distance, y1 - ny * distance),
    ]
    shape = "line_expand" if canvas.draw_shape == "line_expand" else "obb_mirror"
    return EditableAnnotation(canvas.current_class_id, shape, points)
