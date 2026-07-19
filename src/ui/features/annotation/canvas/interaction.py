from __future__ import annotations

from src.services.annotation import EditableAnnotation
from src.shared.qt import Qt
from src.ui.features.annotation.canvas.editing import AnnotationCanvasEditingMixin


class AnnotationCanvasInteractionMixin(AnnotationCanvasEditingMixin):
    def mousePressEvent(self, event):  # noqa: N802 - Qt API name
        if self.pixmap is None:
            return
        self.set_crosshair_position(event.position())
        image_point = self._widget_to_image(event.position())
        if event.button() == Qt.MouseButton.RightButton:
            if image_point is not None:
                hit_index = self._hit_test(image_point)
                if hit_index >= 0:
                    self.selected_index = hit_index
                    self.hovered_index = hit_index
                    self._emit_selection()
                    self._update_hover_cursor()
                    self.update()
            self._show_context_menu(event.globalPosition().toPoint())
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self.draw_shape == "select":
            if image_point is None:
                self._clear_selection()
                self._update_hover_cursor()
                self.update()
                return
            handle_hit = self._find_handle(image_point)
            if handle_hit is not None:
                annotation_index, handle = handle_hit
                self.selected_index = annotation_index
                self.hovered_index = annotation_index
                self.hovered_handle = handle
                self._emit_selection()
                self.active_handle = handle
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                self.update()
                return
            hit_index = self._hit_test(image_point)
            if hit_index >= 0:
                self.selected_index = hit_index
                self._emit_selection()
                if hit_index == self.selected_index:
                    self.move_anchor = image_point
                    self.setCursor(Qt.CursorShape.ClosedHandCursor)
                self.update()
                return
            self._clear_selection()
            self._update_hover_cursor()
            self.update()
            return
        if image_point is None:
            self._clear_selection()
            self.update()
            return
        self._clear_selection()
        if self.draw_shape in {"obb_mirror", "obb_single", "line_expand"}:
            if self.draw_shape == "line_expand" and self.quick_draw:
                self.drag_start = image_point
                self.drag_current = image_point
                self.update()
                return
            self._handle_rotated_shape_click(image_point)
            self.update()
            return
        if self.draw_shape == "circle":
            if self.quick_draw:
                self.drag_start = image_point
                self.drag_current = image_point
            else:
                self._handle_two_click_shape_click(image_point)
            self.update()
            return
        if self.draw_shape == "polygon":
            self._handle_polygon_click(image_point)
            self.update()
            return
        if self.quick_draw:
            self.drag_start = image_point
            self.drag_current = image_point
        else:
            self._handle_two_click_shape_click(image_point)
        self.update()

    def mouseMoveEvent(self, event):  # noqa: N802 - Qt API name
        self.set_crosshair_position(event.position())
        image_point = self._widget_to_image(event.position(), clamp=True)
        if self.draw_shape == "select":
            self._update_hover_state(image_point)
        elif self.draw_shape == "polygon":
            self._update_polygon_hover_state(image_point)
        if self.active_handle is not None and 0 <= self.selected_index < len(self.annotations):
            if image_point is not None:
                self._update_selected_handle(image_point)
                self.update()
            return
        if self.move_anchor is not None and 0 <= self.selected_index < len(self.annotations):
            if image_point is not None:
                dx = image_point[0] - self.move_anchor[0]
                dy = image_point[1] - self.move_anchor[1]
                if dx or dy:
                    self._move_selected_annotation(dx, dy)
                    self.move_anchor = image_point
                    self.update()
            return
        if self.draw_shape == "line_expand" and self.quick_draw and self.drag_start is not None:
            self.drag_current = image_point
            self.update()
            return
        if self.obb_first is not None:
            if self.obb_second is not None:
                if image_point is not None:
                    self.drag_current = image_point
                    self.update()
            elif image_point is not None:
                self.preview_line_end = image_point
                self.update()
            return
        if self.polygon_points:
            if image_point is not None:
                self.preview_line_end = image_point
                self.update()
            return
        if self.drag_start is None:
            return
        self.drag_current = image_point
        self.update()

    def mouseReleaseEvent(self, event):  # noqa: N802 - Qt API name
        if self.active_handle is not None:
            self.active_handle = None
            self._emit_changed()
            self._update_hover_cursor()
            self.update()
            return
        if self.move_anchor is not None:
            self.move_anchor = None
            self._emit_changed()
            self._update_hover_cursor()
            self.update()
            return
        if self.draw_shape == "line_expand" and self.quick_draw:
            if event.button() != Qt.MouseButton.LeftButton or self.drag_start is None:
                return
            image_point = self._widget_to_image(event.position())
            if image_point is not None:
                annotation = self._make_obb_annotation(self.drag_start, image_point, None)
                if annotation is not None:
                    self._finish_annotation(annotation)
                else:
                    self._reset_transient_draw_state()
            self.update()
            return
        if self.draw_shape in {"obb_mirror", "obb_single", "line_expand", "polygon"}:
            return
        if not self.quick_draw:
            return
        if event.button() != Qt.MouseButton.LeftButton or self.drag_start is None:
            return
        image_point = self._widget_to_image(event.position())
        if image_point is not None:
            annotation = self._make_annotation(self.drag_start, image_point)
            if annotation is not None:
                self._finish_annotation(annotation)
            else:
                self._reset_transient_draw_state()
        self.update()

    def leaveEvent(self, event):  # noqa: N802 - Qt API name
        super().leaveEvent(event)
        self.crosshair_position = None
        self.hovered_index = -1
        self.hovered_handle = None
        self.hovered_polygon_close_index = -1
        if self.active_handle is None and self.move_anchor is None:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def enterEvent(self, event):  # noqa: N802 - Qt API name
        super().enterEvent(event)
        self.set_crosshair_position(event.position())
        self._update_hover_cursor()
        self.update()

    def keyPressEvent(self, event):  # noqa: N802 - Qt API name
        if event.key() == Qt.Key.Key_Delete:
            self.delete_selected()
            return
        if event.key() == Qt.Key.Key_Escape:
            if self._cancel_current_drawing():
                self.update()
                return
            if self.draw_shape == "select" and self._clear_selection():
                self._update_hover_cursor()
                self.update()
                return
        super().keyPressEvent(event)

    def _rebuild_rotated_rect_from_corner(
        self,
        points: list[tuple[float, float]],
        corner_index: int,
        moved_point: tuple[float, float],
    ) -> list[tuple[float, float]] | None:
        if len(points) != 4:
            return None
        p0, p1, p2, p3 = points
        ux = p1[0] - p0[0]
        uy = p1[1] - p0[1]
        vx = p3[0] - p0[0]
        vy = p3[1] - p0[1]
        u_len = (ux * ux + uy * uy) ** 0.5
        v_len = (vx * vx + vy * vy) ** 0.5
        if u_len < 1 or v_len < 1:
            return None
        ux /= u_len
        uy /= u_len
        vx /= v_len
        vy /= v_len
        opposite_index = (corner_index + 2) % 4
        fixed = points[opposite_index]
        dx = moved_point[0] - fixed[0]
        dy = moved_point[1] - fixed[1]
        proj_u = dx * ux + dy * uy
        proj_v = dx * vx + dy * vy
        if abs(proj_u) < 3 or abs(proj_v) < 3:
            return None
        corner = moved_point
        corner_u = (fixed[0] + proj_u * ux, fixed[1] + proj_u * uy)
        corner_v = (fixed[0] + proj_v * vx, fixed[1] + proj_v * vy)
        if corner_index == 0:
            return [corner, corner_v, fixed, corner_u]
        if corner_index == 1:
            return [corner_v, corner, corner_u, fixed]
        if corner_index == 2:
            return [fixed, corner_u, corner, corner_v]
        return [corner_u, fixed, corner_v, corner]
