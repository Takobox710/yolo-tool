from __future__ import annotations

from src.services.annotation.annotation_models import EditableAnnotation


def annotation_contains_point(
    annotation: EditableAnnotation,
    point: tuple[float, float],
) -> bool:
    """Return whether a non-keypoint annotation contains an image-space point."""
    if annotation.shape == "point" or not annotation.points:
        return False
    if annotation.shape == "circle":
        left, top, right, bottom = detect_points_to_rect(annotation.points)
        center_x = (left + right) / 2
        center_y = (top + bottom) / 2
        radius = max((right - left) / 2, (bottom - top) / 2)
        dx = point[0] - center_x
        dy = point[1] - center_y
        return dx * dx + dy * dy <= radius * radius + 1e-6
    return polygon_contains_point(annotation.points, point)


def uncontained_keypoint_indices(annotations: list[EditableAnnotation]) -> set[int]:
    """Find point annotations that are outside every non-point annotation."""
    containers = [annotation for annotation in annotations if annotation.shape != "point"]
    return {
        index
        for index, annotation in enumerate(annotations)
        if annotation.shape == "point"
        and annotation.points
        and not any(annotation_contains_point(container, annotation.points[0]) for container in containers)
    }


def polygon_contains_point(
    points: list[tuple[float, float]],
    point: tuple[float, float],
) -> bool:
    if len(points) < 3:
        return False
    px, py = point
    inside = False
    for index, (x1, y1) in enumerate(points):
        x2, y2 = points[(index + 1) % len(points)]
        if _point_on_segment(point, (x1, y1), (x2, y2)):
            return True
        intersects = ((y1 > py) != (y2 > py)) and (
            px < (x2 - x1) * (py - y1) / ((y2 - y1) or 1e-9) + x1
        )
        if intersects:
            inside = not inside
    return inside


def _point_on_segment(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> bool:
    px, py = point
    x1, y1 = start
    x2, y2 = end
    cross = (px - x1) * (y2 - y1) - (py - y1) * (x2 - x1)
    if abs(cross) > 1e-6:
        return False
    return min(x1, x2) - 1e-6 <= px <= max(x1, x2) + 1e-6 and min(y1, y2) - 1e-6 <= py <= max(y1, y2) + 1e-6


def detect_points_to_rect(points: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def points_to_min_area_obb(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if len(points) < 3:
        left, top, right, bottom = detect_points_to_rect(points)
        return [(left, top), (right, top), (right, bottom), (left, bottom)]
    import cv2
    import numpy as np

    box = cv2.boxPoints(cv2.minAreaRect(np.asarray(points, dtype=np.float32)))
    return [tuple(map(float, point)) for point in box]


def line_points_to_obb(
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


__all__ = [
    "annotation_contains_point",
    "detect_points_to_rect",
    "line_points_to_obb",
    "points_to_min_area_obb",
    "polygon_contains_point",
    "uncontained_keypoint_indices",
]
