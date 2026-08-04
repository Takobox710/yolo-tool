from __future__ import annotations

from src.services.annotation import _detect_points_to_rect
from src.shared.qt import Qt
from src.ui.features.annotation.canvas import configuration as canvas_configuration
from src.ui.features.annotation.canvas.geometry import (
    image_rect,
    image_to_widget,
    make_annotation,
    make_obb_annotation,
    widget_to_image,
)
from src.services.annotation.history import snapshot_annotations


class AnnotationCanvasCommandMixin:
    def set_line_expand_config(self, enabled: bool, pixels: int) -> None:
        canvas_configuration.set_line_expand_config(self, enabled, pixels)

    def set_optimize_mirror_edit(self, enabled: bool) -> None:
        canvas_configuration.set_optimize_mirror_edit(self, enabled)

    def set_interaction_config(self, continuous_draw: bool, quick_draw: bool) -> None:
        canvas_configuration.set_interaction_config(self, continuous_draw, quick_draw)

    def set_show_annotation_names(self, enabled: bool) -> None:
        canvas_configuration.set_show_annotation_names(self, enabled)

    def set_show_canvas_status(self, enabled: bool) -> None:
        canvas_configuration.set_show_canvas_status(self, enabled)

    def set_crosshair_position(self, point) -> None:
        canvas_configuration.set_crosshair_position(self, point)

    def delete_selected(self) -> bool:
        if 0 <= self.selected_index < len(self.annotations):
            before = snapshot_annotations(self.annotations)
            focus_index = self.selected_index
            del self.annotations[self.selected_index]
            self.selected_index = -1
            self.hovered_index = -1
            self.hovered_handle = None
            self._emit_annotation_mutation(before, focus_index)
            self._emit_selection()
            self._update_hover_cursor()
            self.update()
            return True
        return False

    def _image_rect(self):
        return image_rect(self)

    def _image_to_widget(self, point: tuple[float, float]):
        return image_to_widget(self, point)

    def _widget_to_image(self, point, clamp: bool = False):
        return widget_to_image(self, point, clamp=clamp)

    def _make_annotation(self, start: tuple[float, float], end: tuple[float, float]):
        return make_annotation(self, start, end)

    def _make_obb_annotation(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        width_point: tuple[float, float] | None,
    ):
        return make_obb_annotation(self, start, end, width_point)

    @staticmethod
    def _detect_points_to_rect(points):
        return _detect_points_to_rect(points)

    @staticmethod
    def _pointing_hand_cursor():
        return Qt.CursorShape.PointingHandCursor

    @staticmethod
    def _arrow_cursor():
        return Qt.CursorShape.ArrowCursor

    @staticmethod
    def _crosshair_cursor():
        return Qt.CursorShape.CrossCursor

    @staticmethod
    def _polygon_contains_point(points: list[tuple[float, float]], point: tuple[float, float]) -> bool:
        inside = False
        px, py = point
        count = len(points)
        for index in range(count):
            x1, y1 = points[index]
            x2, y2 = points[(index + 1) % count]
            intersects = ((y1 > py) != (y2 > py)) and (
                px < (x2 - x1) * (py - y1) / ((y2 - y1) or 1e-9) + x1
            )
            if intersects:
                inside = not inside
        return inside

__all__ = ["AnnotationCanvasCommandMixin"]
