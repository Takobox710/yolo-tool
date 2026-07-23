from __future__ import annotations

from math import atan2, cos, pi, sin, tau

from src.ui.features.annotation.canvas.geometry import (
    mirror_geometry,
    rebuild_mirror_points,
)

class AnnotationCanvasEditingMixin:
    def _update_selected_handle(self, point: tuple[float, float]) -> None:
        if self.active_handle is None or not (0 <= self.selected_index < len(self.annotations)):
            return
        annotation = self.annotations[self.selected_index]
        handle_type, handle_index = self.active_handle
        if annotation.shape == "circle":
            self._resize_circle_annotation(annotation, handle_type, point)
            return
        if (
            annotation.shape in {"obb_mirror", "line_expand"}
            and self.optimize_mirror_edit
            and handle_type in {"mirror-center", "mirror-width"}
        ):
            self._update_optimized_mirror_handle(annotation, handle_type, handle_index, point)
            return
        if annotation.shape == "rect" and handle_type == "point":
            opposite = annotation.points[(handle_index + 2) % 4]
            left, right = sorted((point[0], opposite[0]))
            top, bottom = sorted((point[1], opposite[1]))
            annotation.points = [(left, top), (right, top), (right, bottom), (left, bottom)]
            return
        if annotation.shape in {"obb", "obb_mirror", "obb_single", "line_expand"} and handle_type == "point":
            rect_points = self._rebuild_rotated_rect_from_corner(annotation.points, handle_index, point)
            if rect_points is not None:
                annotation.points = rect_points
            return
        if annotation.shape in {"obb", "obb_mirror", "obb_single", "line_expand"} and handle_type == "rotate":
            self._rotate_selected_obb(annotation, handle_index, point)
            return
        if handle_type == "point" and 0 <= handle_index < len(annotation.points):
            annotation.points[handle_index] = point

    def _update_optimized_mirror_handle(
        self,
        annotation,
        handle_type: str,
        handle_index: int,
        point: tuple[float, float],
    ) -> None:
        geometry = mirror_geometry(annotation.points)
        if geometry is None or not 0 <= handle_index < 2:
            return
        center_start, center_end, signed_half_width = geometry
        if handle_type == "mirror-center":
            if handle_index == 0:
                center_start = point
            else:
                center_end = point
        else:
            dx = center_end[0] - center_start[0]
            dy = center_end[1] - center_start[1]
            length = (dx * dx + dy * dy) ** 0.5
            if length < 1e-6:
                return
            nx = -dy / length
            ny = dx / length
            distance = abs((point[0] - center_start[0]) * nx + (point[1] - center_start[1]) * ny)
            signed_half_width = max(3.0, distance) * (-1.0 if signed_half_width < 0 else 1.0)
        points = rebuild_mirror_points(center_start, center_end, signed_half_width)
        if points is not None:
            annotation.points = points

    def _rotate_selected_obb(
        self,
        annotation,
        edge_index: int,
        point: tuple[float, float],
    ) -> None:
        if len(annotation.points) != 4 or not 0 <= edge_index < 4:
            return
        center_x = sum(item[0] for item in annotation.points) / 4
        center_y = sum(item[1] for item in annotation.points) / 4
        handle_start = annotation.points[edge_index]
        handle_end = annotation.points[(edge_index + 1) % 4]
        start_x = (handle_start[0] + handle_end[0]) / 2 - center_x
        start_y = (handle_start[1] + handle_end[1]) / 2 - center_y
        target_x = point[0] - center_x
        target_y = point[1] - center_y
        if start_x * start_x + start_y * start_y < 1e-9 or target_x * target_x + target_y * target_y < 1e-9:
            return
        delta = atan2(target_y, target_x) - atan2(start_y, start_x)
        if delta > pi:
            delta -= tau
        elif delta < -pi:
            delta += tau
        cosine = cos(delta)
        sine = sin(delta)
        annotation.points = [
            (
                center_x + (x_pos - center_x) * cosine - (y_pos - center_y) * sine,
                center_y + (x_pos - center_x) * sine + (y_pos - center_y) * cosine,
            )
            for x_pos, y_pos in annotation.points
        ]

    def _resize_circle_annotation(self, annotation, handle_type, point) -> None:
        x1, y1, x2, y2 = self._detect_points_to_rect(annotation.points)
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        radius = max((x2 - x1) / 2, (y2 - y1) / 2)
        radius_point = annotation.radius_point or (center_x + radius, center_y)
        if handle_type == "center":
            dx = point[0] - center_x
            dy = point[1] - center_y
            center_x, center_y = point
            radius_point = (radius_point[0] + dx, radius_point[1] + dy)
        elif handle_type == "radius":
            radius = max(
                3.0,
                ((point[0] - center_x) ** 2 + (point[1] - center_y) ** 2) ** 0.5,
            )
            radius_point = point
        annotation.points = [
            (center_x - radius, center_y - radius),
            (center_x + radius, center_y - radius),
            (center_x + radius, center_y + radius),
            (center_x - radius, center_y + radius),
        ]
        annotation.radius_point = radius_point

    def _move_selected_annotation(self, dx: float, dy: float) -> None:
        if not (0 <= self.selected_index < len(self.annotations)):
            return
        annotation = self.annotations[self.selected_index]
        annotation.points = [(x_pos + dx, y_pos + dy) for x_pos, y_pos in annotation.points]
        if annotation.shape == "circle" and annotation.radius_point is not None:
            annotation.radius_point = (
                annotation.radius_point[0] + dx,
                annotation.radius_point[1] + dy,
            )
