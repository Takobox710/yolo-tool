from __future__ import annotations

DRAW_SHAPE_LABELS = {
    "select": "编辑",
    "rect": "矩形框",
    "obb_single": "有向矩形",
    "obb_mirror": "镜像有向矩形",
    "polygon": "多边形",
    "circle": "圆形",
    "line_expand": "直线扩展",
}


class AnnotationCanvasStatusMixin:
    def _canvas_status_text(self) -> str:
        return DRAW_SHAPE_LABELS.get(self.draw_shape, self.draw_shape)

    def _notify_canvas_status_changed(self) -> None:
        callback = getattr(self, "status_changed_callback", None)
        if callable(callback):
            callback()
