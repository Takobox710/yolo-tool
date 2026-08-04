from __future__ import annotations

from pathlib import Path

from src.services.annotation import EditableAnnotation, _detect_points_to_rect
from src.services.annotation.history import snapshot_annotations
from src.shared.qt import Qt
from src.ui.features.annotation.canvas.geometry import pixmap_from_path
from src.ui.features.annotation.canvas.state import reset_transient_draw_state


SAM_SUPPORTED_SHAPES = {"rect", "obb_single", "obb_mirror", "polygon"}


class AnnotationCanvasLifecycleMixin:
    def set_image(
        self,
        image_path: Path | None,
        annotations: list[EditableAnnotation],
        class_names: list[str],
    ) -> None:
        self.image_path = image_path
        self.annotations = annotations
        self.class_names = class_names
        self.selected_index = -1
        reset_transient_draw_state(self)
        self.hovered_handle = None
        self.hovered_index = -1
        self.crosshair_position = None
        self.flash_index = -1
        self._mutation_before = None
        self._mutation_focus_index = None
        self.clear_sam_preview()
        self._flash_timer.stop()
        self._update_hover_cursor()
        if image_path is None:
            self.pixmap = None
            self.image_size = (0, 0)
        else:
            self.pixmap = pixmap_from_path(image_path)
            self.image_size = (self.pixmap.width(), self.pixmap.height())
        self._emit_selection()
        self.update()
        if self.sam_image_callback is not None:
            self.sam_image_callback(image_path)

    def set_class_names(self, class_names: list[str]) -> None:
        self.class_names = class_names
        self.update()

    def set_current_class(self, class_id: int) -> None:
        self.current_class_id = max(0, class_id)
        self.update()

    def set_draw_shape(self, shape: str) -> None:
        if self.sam_assist_enabled and shape not in SAM_SUPPORTED_SHAPES | {"select"}:
            return
        was_editing = self.draw_shape == "select"
        self.draw_shape = shape
        self.cancel_sam_hover()
        reset_transient_draw_state(self)
        self.hovered_handle = None
        if was_editing and shape != "select":
            self._clear_selection()
        self.crosshair_position = None
        self._update_hover_cursor()
        self.update()
        self._notify_canvas_status_changed()

    def set_sam_assist_enabled(self, enabled: bool) -> None:
        self.sam_assist_enabled = bool(enabled)
        if self.sam_assist_enabled:
            self.crosshair_position = None
        self.clear_sam_preview()
        reset_transient_draw_state(self)
        if self.sam_assist_enabled and self.draw_shape not in SAM_SUPPORTED_SHAPES | {"select"}:
            self.set_draw_shape("rect")
        self._update_hover_cursor()
        self.update()
        self._notify_canvas_status_changed()

    def set_sam_preview(self, shape: str, geometry: dict, generation: int) -> None:
        geometry_key = {
            "rect": "rectangle",
            "obb_single": "oriented_rectangle",
            "obb_mirror": "oriented_rectangle",
            "polygon": "polygon",
        }.get(shape)
        raw_points = geometry.get(geometry_key, []) if geometry_key else []
        points = [tuple(map(float, point)) for point in raw_points if len(point) >= 2]
        minimum_points = 3 if shape == "polygon" else 4
        if shape != self.draw_shape or len(points) < minimum_points:
            self.clear_sam_preview()
            return
        self.sam_preview_annotation = EditableAnnotation(self.current_class_id, shape, points)
        self.sam_preview_generation = int(generation)
        self.update()

    def clear_sam_preview(self) -> None:
        changed = self.sam_preview_annotation is not None
        self.sam_preview_annotation = None
        self.sam_preview_generation = 0
        if changed:
            self.update()

    def cancel_sam_hover(self) -> None:
        self.clear_sam_preview()
        if self.sam_cancel_hover_callback is not None:
            self.sam_cancel_hover_callback()

    def _confirm_sam_preview(self) -> bool:
        preview = self.sam_preview_annotation
        if preview is None or preview.shape != self.draw_shape:
            return False
        annotation = EditableAnnotation(
            self.current_class_id,
            preview.shape,
            list(preview.points),
        )
        self.cancel_sam_hover()
        self._finish_annotation(annotation, flash=True)
        return True

    def _sam_shape_supported(self) -> bool:
        return self.sam_assist_enabled and self.draw_shape in SAM_SUPPORTED_SHAPES

    def _clear_selection(self) -> bool:
        had_selection = self.selected_index >= 0
        self.selected_index = -1
        self.hovered_index = -1
        self.hovered_handle = None
        if had_selection:
            self._emit_selection()
            self._update_hover_cursor()
        return had_selection

__all__ = ["AnnotationCanvasLifecycleMixin"]
