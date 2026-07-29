from __future__ import annotations

import math


def circle_bounds(points: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    if 2 <= len(points) < 4:
        (center_x, center_y), (edge_x, edge_y) = points[:2]
        radius = ((edge_x - center_x) ** 2 + (edge_y - center_y) ** 2) ** 0.5
        return (
            center_x - radius,
            center_y - radius,
            center_x + radius,
            center_y + radius,
        )
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def circle_polygon(
    points: list[tuple[float, float]], point_count: int = 32
) -> list[tuple[float, float]]:
    """Return a deterministic polygon approximation of a Labelme circle."""
    if len(points) < 2 or point_count < 3:
        return []
    (center_x, center_y), (edge_x, edge_y) = points[:2]
    radius = math.hypot(edge_x - center_x, edge_y - center_y)
    if radius <= 0:
        return []
    return [
        (
            center_x + radius * math.cos(2 * math.pi * index / point_count),
            center_y + radius * math.sin(2 * math.pi * index / point_count),
        )
        for index in range(point_count)
    ]
