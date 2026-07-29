from __future__ import annotations


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


__all__ = ["detect_points_to_rect", "line_points_to_obb", "points_to_min_area_obb"]
