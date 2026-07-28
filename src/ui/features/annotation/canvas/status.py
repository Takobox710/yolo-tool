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
        shape_text = DRAW_SHAPE_LABELS.get(self.draw_shape, self.draw_shape)
        if not getattr(self, "sam_assist_enabled", False):
            return shape_text
        state_text = {
            "loading_model": "加载中",
            "model_ready": "模型就绪",
            "waiting_image": "等待图片",
            "encoding_image": "编码中",
            "ready": "就绪",
            "predicting": "推理中",
            "error": "错误",
        }.get(getattr(self, "sam_state", ""), "已开启")
        return f"SAM 智能标注 · {shape_text} · {state_text}"

    def _notify_canvas_status_changed(self) -> None:
        callback = getattr(self, "status_changed_callback", None)
        if callable(callback):
            callback()
