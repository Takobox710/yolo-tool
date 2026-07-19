from __future__ import annotations


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
