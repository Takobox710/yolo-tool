from __future__ import annotations

from math import hypot

from src.services.annotation import EditableAnnotation
from src.ui.features.annotation.canvas.geometry import mirror_edit_points


HANDLE_RADIUS = 4.5
HANDLE_HIT_RADIUS_FACTOR = 2.0


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

    def _annotation_handles(
        self,
        annotation: EditableAnnotation,
        reference_point: tuple[float, float] | None = None,
    ) -> list[tuple[str, tuple[float, float]]]:
        if annotation.shape == "circle":
            x1, y1, x2, y2 = self._detect_points_to_rect(annotation.points)
            center = ((x1 + x2) / 2, (y1 + y2) / 2)
            radius = max((x2 - x1) / 2, (y2 - y1) / 2)
            radius_point = annotation.radius_point or (center[0] + radius, center[1])
            if reference_point is not None:
                direction = (
                    reference_point[0] - center[0],
                    reference_point[1] - center[1],
                )
                distance = hypot(*direction)
                if distance > 1e-6:
                    radius_point = (
                        center[0] + direction[0] / distance * radius,
                        center[1] + direction[1] / distance * radius,
                    )
            return [("center", center), ("radius", radius_point)]
        if (
            annotation.shape in {"obb_mirror", "line_expand"}
            and self.optimize_mirror_edit
        ):
            mirror_points = mirror_edit_points(annotation.points)
            if mirror_points is not None:
                center_start, center_end, side_start, side_end = mirror_points
                return [
                    ("mirror-center-0", center_start),
                    ("mirror-center-1", center_end),
                    ("mirror-width-0", side_start),
                    ("mirror-width-1", side_end),
                ]
        handles = [(f"point-{index}", point) for index, point in enumerate(annotation.points)]
        if annotation.shape in {"obb", "obb_mirror", "obb_single", "line_expand"} and len(annotation.points) == 4:
            handles.extend(
                (
                    f"rotate-{index}",
                    (
                        (annotation.points[index][0] + annotation.points[(index + 1) % 4][0]) / 2,
                        (annotation.points[index][1] + annotation.points[(index + 1) % 4][1]) / 2,
                    ),
                )
                for index in range(4)
            )
        return handles

    def _hit_annotation_handle(self, point: tuple[float, float], annotation_index: int) -> tuple[str, int] | None:
        if not (0 <= annotation_index < len(self.annotations)):
            return None
        radius = self._handle_radius() * HANDLE_HIT_RADIUS_FACTOR
        annotation = self.annotations[annotation_index]
        for handle_type, handle_point in self._annotation_handles(annotation):
            dx = point[0] - handle_point[0]
            dy = point[1] - handle_point[1]
            if dx * dx + dy * dy <= radius * radius:
                if handle_type.startswith("point-"):
                    return ("point", int(handle_type.split("-", 1)[1]))
                if handle_type.startswith("rotate-"):
                    return ("rotate", int(handle_type.split("-", 1)[1]))
                if handle_type.startswith("mirror-center-"):
                    return ("mirror-center", int(handle_type.rsplit("-", 1)[1]))
                if handle_type.startswith("mirror-width-"):
                    return ("mirror-width", int(handle_type.rsplit("-", 1)[1]))
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
