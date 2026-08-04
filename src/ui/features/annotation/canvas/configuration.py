from __future__ import annotations


def set_line_expand_config(canvas, enabled: bool, pixels: int) -> None:
    canvas.line_expand_enabled = bool(enabled)
    canvas.line_expand_pixels = max(1, int(pixels))


def set_optimize_mirror_edit(canvas, enabled: bool) -> None:
    canvas.optimize_mirror_edit = bool(enabled)
    canvas.update()


def set_interaction_config(canvas, continuous_draw: bool, quick_draw: bool) -> None:
    canvas.continuous_draw = bool(continuous_draw)
    canvas.quick_draw = bool(quick_draw)


def set_show_annotation_names(canvas, enabled: bool) -> None:
    canvas.show_annotation_names = bool(enabled)
    canvas.update()


def set_show_canvas_status(canvas, enabled: bool) -> None:
    canvas.show_canvas_status = bool(enabled)
    canvas.update()
    canvas._notify_canvas_status_changed()


def set_crosshair_position(canvas, point) -> None:
    if point is None:
        return
    if canvas.draw_shape != "rect" or canvas.sam_assist_enabled:
        changed = canvas.crosshair_position is not None
        canvas.crosshair_position = None
        if changed:
            canvas.update()
        return
    position = (float(point.x()), float(point.y()))
    if position != canvas.crosshair_position:
        canvas.crosshair_position = position
        canvas.update()
