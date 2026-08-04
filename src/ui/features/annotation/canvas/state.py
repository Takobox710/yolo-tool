from __future__ import annotations


def initialize_canvas_state(canvas) -> None:
    canvas.image_path = None
    canvas.pixmap = None
    canvas.image_size = (0, 0)
    canvas.annotations = []
    canvas.class_names = []
    canvas.current_class_id = 0
    canvas.draw_shape = "select"
    canvas.selected_index = -1
    canvas.hovered_index = -1
    canvas.drag_start = None
    canvas.drag_current = None
    canvas.obb_first = None
    canvas.obb_second = None
    canvas.polygon_points = []
    canvas.preview_line_end = None
    canvas.active_handle = None
    canvas.hovered_handle = None
    canvas.move_anchor = None
    canvas.hovered_polygon_close_index = -1
    canvas.crosshair_position = None
    canvas.line_expand_enabled = False
    canvas.line_expand_pixels = 10
    canvas.optimize_mirror_edit = False
    canvas.continuous_draw = False
    canvas.quick_draw = True
    canvas.flash_index = -1
    canvas.changed_callback = None
    canvas.selection_callback = None
    canvas.save_labelme_callback = None
    canvas.save_yolo_callback = None
    canvas.undo_callback = None
    canvas.redo_callback = None
    canvas.history_callback = None
    canvas.class_change_callback = None
    canvas.save_default_callback = None
    canvas.can_save_labelme = False
    canvas.can_save_yolo = False
    canvas.can_undo = False
    canvas.can_redo = False
    canvas.can_save_default = False
    canvas.show_separate_yolo_save = False
    canvas.show_annotation_names = False
    canvas.show_canvas_status = True
    canvas.status_changed_callback = None
    canvas.sam_assist_enabled = False
    canvas.sam_state = "disabled"
    canvas.sam_model_name = ""
    canvas.sam_preview_annotation = None
    canvas.sam_preview_generation = 0
    canvas.sam_hover_callback = None
    canvas.sam_toggle_callback = None
    canvas.sam_image_callback = None
    canvas.sam_cancel_hover_callback = None
    canvas._mutation_before = None
    canvas._mutation_focus_index = None


def reset_transient_draw_state(canvas) -> None:
    canvas.drag_start = None
    canvas.drag_current = None
    canvas.obb_first = None
    canvas.obb_second = None
    canvas.preview_line_end = None
    canvas.polygon_points = []
    canvas.hovered_polygon_close_index = -1
    canvas.active_handle = None
    canvas.move_anchor = None


def can_show_cancel_drawing_action(canvas) -> bool:
    return (
        canvas.drag_start is not None
        or canvas.obb_first is not None
        or bool(canvas.polygon_points)
    )


def has_selected_annotation(canvas) -> bool:
    return 0 <= canvas.selected_index < len(canvas.annotations)
