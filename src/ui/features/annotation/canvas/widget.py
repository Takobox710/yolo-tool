from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer
from src.services.annotation import EditableAnnotation, _detect_points_to_rect
from src.shared.qt import QSizePolicy, Qt, QWidget
from src.ui.features.annotation.canvas.context_menu import AnnotationCanvasContextMenuMixin
from src.ui.features.annotation.canvas.drawing import AnnotationCanvasDrawingMixin
from src.ui.features.annotation.canvas.geometry import (
    image_rect,
    image_to_widget,
    make_annotation,
    make_obb_annotation,
    pixmap_from_path,
    widget_to_image,
)
from src.ui.features.annotation.canvas.hit_test import AnnotationCanvasHitTestMixin
from src.ui.features.annotation.canvas.interaction import AnnotationCanvasInteractionMixin
from src.ui.features.annotation.canvas.render import AnnotationCanvasRenderMixin
from src.ui.features.annotation.canvas.state import reset_transient_draw_state


class AnnotationCanvas(
    AnnotationCanvasContextMenuMixin,
    AnnotationCanvasDrawingMixin,
    AnnotationCanvasHitTestMixin,
    AnnotationCanvasInteractionMixin,
    AnnotationCanvasRenderMixin,
    QWidget,
):
    def __init__(self):
        super().__init__()
        self.setObjectName("annotationCanvas")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setMinimumSize(420, 360)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.image_path: Path | None = None
        self.pixmap = None
        self.image_size = (0, 0)
        self.annotations: list[EditableAnnotation] = []
        self.class_names: list[str] = []
        self.current_class_id = 0
        self.draw_shape = "select"
        self.selected_index = -1
        self.hovered_index = -1
        self.drag_start: tuple[float, float] | None = None
        self.drag_current: tuple[float, float] | None = None
        self.obb_first: tuple[float, float] | None = None
        self.obb_second: tuple[float, float] | None = None
        self.polygon_points: list[tuple[float, float]] = []
        self.preview_line_end: tuple[float, float] | None = None
        self.active_handle: tuple[str, int] | None = None
        self.hovered_handle: tuple[str, int] | None = None
        self.move_anchor: tuple[float, float] | None = None
        self.hovered_polygon_close_index = -1
        self.crosshair_position: tuple[float, float] | None = None
        self.line_expand_enabled = False
        self.line_expand_pixels = 10
        self.continuous_draw = False
        self.quick_draw = True
        self.flash_index = -1
        self.changed_callback = None
        self.selection_callback = None
        self.save_labelme_callback = None
        self.save_yolo_callback = None
        self.undo_callback = None
        self.save_default_callback = None
        self.can_save_labelme = False
        self.can_save_yolo = False
        self.can_undo = False
        self.can_save_default = False
        self.show_separate_yolo_save = False
        self.show_annotation_names = False
        self._flash_timer = QTimer(self)
        self._flash_timer.setSingleShot(True)
        self._flash_timer.timeout.connect(self._clear_flash)

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

    def set_class_names(self, class_names: list[str]) -> None:
        self.class_names = class_names
        self.update()

    def set_current_class(self, class_id: int) -> None:
        self.current_class_id = max(0, class_id)

    def set_draw_shape(self, shape: str) -> None:
        was_editing = self.draw_shape == "select"
        self.draw_shape = shape
        reset_transient_draw_state(self)
        self.hovered_handle = None
        if was_editing and shape != "select":
            self._clear_selection()
        self.crosshair_position = None
        self._update_hover_cursor()
        self.update()

    def _clear_selection(self) -> bool:
        had_selection = self.selected_index >= 0
        self.selected_index = -1
        self.hovered_index = -1
        self.hovered_handle = None
        if had_selection:
            self._emit_selection()
            self._update_hover_cursor()
        return had_selection

    def set_line_expand_config(self, enabled: bool, pixels: int) -> None:
        self.line_expand_enabled = bool(enabled)
        self.line_expand_pixels = max(1, int(pixels))

    def set_interaction_config(self, continuous_draw: bool, quick_draw: bool) -> None:
        self.continuous_draw = bool(continuous_draw)
        self.quick_draw = bool(quick_draw)

    def set_show_annotation_names(self, enabled: bool) -> None:
        self.show_annotation_names = bool(enabled)
        self.update()

    def set_crosshair_position(self, point) -> None:
        if point is None:
            return
        if self.draw_shape != "rect":
            changed = self.crosshair_position is not None
            self.crosshair_position = None
            if changed:
                self.update()
            return
        position = (float(point.x()), float(point.y()))
        if position != self.crosshair_position:
            self.crosshair_position = position
            self.update()

    def delete_selected(self) -> bool:
        if 0 <= self.selected_index < len(self.annotations):
            del self.annotations[self.selected_index]
            self.selected_index = -1
            self.hovered_index = -1
            self.hovered_handle = None
            self._emit_changed()
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
