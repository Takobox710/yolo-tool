from __future__ import annotations

from src.services.annotation import EditableAnnotation
from src.ui.features.annotation.canvas.state import (
    can_show_cancel_drawing_action,
    has_selected_annotation,
    reset_transient_draw_state,
)


class AnnotationCanvasDrawingMixin:
    def _update_hover_state(self, point: tuple[float, float] | None) -> None:
        if point is None:
            self.hovered_index = -1
            self.hovered_handle = None
            self._update_hover_cursor()
            self.update()
            return
        previous_index = self.hovered_index
        previous_handle = self.hovered_handle
        handle_hit = self._find_handle(point)
        if handle_hit is not None:
            self.hovered_index, self.hovered_handle = handle_hit
        else:
            self.hovered_handle = None
            self.hovered_index = self._hit_test(point)
        self._update_hover_cursor()
        if previous_index != self.hovered_index or previous_handle != self.hovered_handle:
            self.update()

    def _update_hover_cursor(self) -> None:
        if self.active_handle is not None or self.move_anchor is not None:
            return
        if self.draw_shape == "select" and (self.hovered_handle is not None or self.hovered_index >= 0):
            self.setCursor(self._pointing_hand_cursor())
        elif self.draw_shape == "polygon" and self.hovered_polygon_close_index >= 0:
            self.setCursor(self._pointing_hand_cursor())
        elif self.draw_shape != "select":
            self.setCursor(self._crosshair_cursor())
        else:
            self.setCursor(self._arrow_cursor())

    def _update_polygon_hover_state(self, point: tuple[float, float] | None) -> None:
        previous_index = self.hovered_polygon_close_index
        self.hovered_polygon_close_index = -1
        if point is not None:
            closing_index = self._polygon_closing_index(point)
            if closing_index is not None and len(self.polygon_points) >= 3:
                if closing_index == 0 or closing_index >= 2:
                    self.hovered_polygon_close_index = closing_index
        self._update_hover_cursor()
        if previous_index != self.hovered_polygon_close_index:
            self.update()

    def _cancel_current_drawing(self) -> bool:
        if self.drag_start is not None or self.obb_first is not None or self.polygon_points:
            self._reset_transient_draw_state()
            return True
        if self.draw_shape != "select":
            self.set_draw_shape("select")
            return True
        return False

    def _can_show_cancel_drawing_action(self) -> bool:
        return can_show_cancel_drawing_action(self)

    def _has_selected_annotation(self) -> bool:
        return has_selected_annotation(self)

    def _reset_transient_draw_state(self) -> None:
        reset_transient_draw_state(self)

    def _finish_annotation(self, annotation: EditableAnnotation, *, flash: bool = False) -> None:
        self.annotations.append(annotation)
        annotation_index = len(self.annotations) - 1
        self.selected_index = -1
        self.hovered_index = -1
        self.hovered_handle = None
        self._emit_changed()
        self._emit_selection()
        if flash:
            self._flash_annotation(annotation_index)
        if self.continuous_draw:
            self._reset_transient_draw_state()
        else:
            self.set_draw_shape("select")

    def _handle_two_click_shape_click(self, image_point: tuple[float, float]) -> None:
        if self.drag_start is None:
            self.drag_start = image_point
            self.drag_current = image_point
            return
        annotation = self._make_annotation(self.drag_start, image_point)
        if annotation is not None:
            self._finish_annotation(annotation)
        else:
            self._reset_transient_draw_state()

    def _handle_rotated_shape_click(self, image_point: tuple[float, float]) -> None:
        if self.obb_first is None:
            self.obb_first = image_point
            self.obb_second = None
            self.preview_line_end = image_point
            return
        if self.draw_shape == "line_expand":
            annotation = self._make_obb_annotation(self.obb_first, image_point, None)
            if annotation is not None:
                self._finish_annotation(annotation)
            else:
                self._reset_transient_draw_state()
            return
        if self.obb_second is None:
            self.obb_second = image_point
            self.drag_current = image_point
            self.preview_line_end = None
            return
        annotation = self._make_obb_annotation(self.obb_first, self.obb_second, image_point)
        if annotation is not None:
            self._finish_annotation(annotation)
        else:
            self._reset_transient_draw_state()

    def _handle_polygon_click(self, image_point: tuple[float, float]) -> None:
        closing_index = self._polygon_closing_index(image_point)
        if closing_index is not None and (closing_index == 0 or closing_index >= 2) and len(self.polygon_points) >= 3:
            points = list(self.polygon_points)
            if closing_index != 0:
                points = points[: closing_index + 1]
            annotation = EditableAnnotation(self.current_class_id, "polygon", points)
            self._finish_annotation(annotation, flash=True)
            return
        self.polygon_points.append(image_point)
        self.preview_line_end = image_point

    def _polygon_closing_index(self, image_point: tuple[float, float]) -> int | None:
        radius_sq = max(36.0, self._handle_radius() ** 2 * 4)
        for index, point in enumerate(self.polygon_points):
            dx = image_point[0] - point[0]
            dy = image_point[1] - point[1]
            if dx * dx + dy * dy <= radius_sq:
                return index
        return None

    def _flash_annotation(self, index: int) -> None:
        self.flash_index = index
        self._flash_timer.start(180)

    def _clear_flash(self) -> None:
        self.flash_index = -1
        self.update()

    def _emit_changed(self) -> None:
        if self.changed_callback:
            self.changed_callback()

    def _emit_selection(self) -> None:
        if self.selection_callback:
            self.selection_callback(self.selected_index)
