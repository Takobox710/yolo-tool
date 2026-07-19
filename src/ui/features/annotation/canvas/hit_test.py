from __future__ import annotations

from src.services.annotation import EditableAnnotation


HANDLE_RADIUS = 4.5


class AnnotationCanvasHitTestMixin:
    def _hit_test(self, point: tuple[float, float]) -> int:
        for index in reversed(range(len(self.annotations))):
            annotation = self.annotations[index]
            if annotation.shape == "circle":
                x1, y1, x2, y2 = self._detect_points_to_rect(annotation.points)
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2
                radius = max((x2 - x1) / 2, (y2 - y1) / 2)
                dx = point[0] - center_x
                dy = point[1] - center_y
                if dx * dx + dy * dy <= radius * radius:
                    return index
                continue
            if annotation.shape in {"obb", "obb_mirror", "obb_single", "line_expand", "polygon"}:
                if self._polygon_contains_point(annotation.points, point):
                    return index
                continue
            x1, y1, x2, y2 = self._detect_points_to_rect(annotation.points)
            margin = max(6.0, min(self.image_size or (4, 4)) * 0.005)
            if x1 - margin <= point[0] <= x2 + margin and y1 - margin <= point[1] <= y2 + margin:
                return index
        return -1

    def _handle_radius(self) -> float:
        return HANDLE_RADIUS

    def _annotation_handles(self, annotation: EditableAnnotation) -> list[tuple[str, tuple[float, float]]]:
        if annotation.shape == "circle":
            x1, y1, x2, y2 = self._detect_points_to_rect(annotation.points)
            center = ((x1 + x2) / 2, (y1 + y2) / 2)
            radius = max((x2 - x1) / 2, (y2 - y1) / 2)
            return [("center", center), ("radius", (center[0] + radius, center[1]))]
        return [(f"point-{index}", point) for index, point in enumerate(annotation.points)]

    def _hit_annotation_handle(self, point: tuple[float, float], annotation_index: int) -> tuple[str, int] | None:
        if not (0 <= annotation_index < len(self.annotations)):
            return None
        radius = self._handle_radius() * 1.6
        annotation = self.annotations[annotation_index]
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

    def _hit_handle(self, point: tuple[float, float]) -> tuple[str, int] | None:
        if not (0 <= self.selected_index < len(self.annotations)):
            return None
        return self._hit_annotation_handle(point, self.selected_index)

    def _find_handle(self, point: tuple[float, float]) -> tuple[int, tuple[str, int]] | None:
        for index in reversed(range(len(self.annotations))):
            handle = self._hit_annotation_handle(point, index)
            if handle is not None:
                return index, handle
        return None
