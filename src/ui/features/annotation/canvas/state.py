from __future__ import annotations


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
