from __future__ import annotations


class AnnotationCanvasEditingMixin:
    def _update_selected_handle(self, point: tuple[float, float]) -> None:
        if self.active_handle is None or not (0 <= self.selected_index < len(self.annotations)):
            return
        annotation = self.annotations[self.selected_index]
        handle_type, handle_index = self.active_handle
        if annotation.shape == "circle":
            self._resize_circle_annotation(annotation, handle_type, point)
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
        if handle_type == "point" and 0 <= handle_index < len(annotation.points):
            annotation.points[handle_index] = point

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
