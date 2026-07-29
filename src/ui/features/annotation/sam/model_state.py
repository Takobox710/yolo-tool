from __future__ import annotations

from typing import Any

from src.services.annotation import SamModelSpec, find_sam_model_specs, preferred_sam_model


class SamModelStateMixin:

    def parameters(self) -> dict[str, Any]:
        settings = self.page.context.settings.annotation.sam_assist
        return {
            "multimask_output": bool(settings.multimask_output),
            "minimum_score": float(settings.minimum_score),
            "minimum_area": int(settings.minimum_area),
            "polygon_simplification_ratio": float(
                settings.polygon_simplification_ratio
            ),
        }


    def select_model(self, model_key: str) -> None:
        selected = next((model for model in self.models if model.key == model_key), None)
        if selected is None or selected == self.selected_model:
            return
        self.selected_model = selected
        self.page.context.settings.annotation.sam_assist.model_path = selected.key
        self.page.save_settings()
        self.page.canvas.sam_model_name = (
            selected.display_name if selected.supports_assist else ""
        )
        if not selected.supports_assist and self.enabled:
            self.set_enabled(False)
        elif selected.supports_assist and (self.enabled or self._worker is not None):
            self._load_selected_model()
        self.state_changed.emit()


    def refresh_models(self) -> None:
        saved = self.page.context.settings.annotation.sam_assist.model_path
        current_name = self.selected_model.key if self.selected_model is not None else ""
        self.models = find_sam_model_specs(self.page.project_root())
        self.selected_model = preferred_sam_model(self.models, current_name or saved)
        self.page.canvas.sam_model_name = (
            self.selected_model.display_name
            if self.selected_model is not None and self.selected_model.supports_assist
            else ""
        )
        self.state_changed.emit()


    def apply_parameters(self, values: dict[str, Any]) -> dict[str, Any]:
        normalized = {
            "multimask_output": bool(values.get("multimask_output", False)),
            "minimum_score": max(
                0.0, min(1.0, float(values.get("minimum_score", 0.0)))
            ),
            "minimum_area": max(
                1, min(100_000_000, int(values.get("minimum_area", 4)))
            ),
            "polygon_simplification_ratio": max(
                0.0,
                min(
                    0.015,
                    float(values.get("polygon_simplification_ratio", 0.002)),
                ),
            ),
        }
        if normalized == self.parameters():
            return normalized
        settings = self.page.context.settings.annotation.sam_assist
        settings.multimask_output = normalized["multimask_output"]
        settings.minimum_score = normalized["minimum_score"]
        settings.minimum_area = normalized["minimum_area"]
        settings.polygon_simplification_ratio = normalized[
            "polygon_simplification_ratio"
        ]
        self.page.save_settings()
        self.page.canvas.clear_sam_preview()
        self.cancel_hover()
        self.state_changed.emit()
        return normalized


    def set_enabled(self, enabled: bool) -> bool:
        requested = bool(enabled)
        if requested == self.enabled:
            return self.enabled
        if requested and self.selected_model is None:
            self._show_error("未找到可用的 SAM 标注模型。")
            return False
        if requested and not self.selected_model.supports_assist:
            self._show_error(
                "该 SAM 文件已显示在模型列表中，但无法从文件名确定可用的画布标注运行后端。"
            )
            return False
        self.enabled = requested
        self.page.canvas.set_sam_assist_enabled(requested)
        if requested:
            if self._worker is None:
                self._load_selected_model()
            elif not self._model_loaded:
                self._set_state("loading_model")
            elif self.page.current_image_path is None:
                self._set_state("waiting_image")
            elif not self._image_ready:
                self._encode_image(self.page.current_image_path)
            else:
                self._set_state("ready")
        else:
            self.hover_generation += 1
            self._minimum_hover_generation = self.hover_generation
            self._hover_timer.stop()
            self._hover_payload = None
            self._hover_inflight = False
            self._hover_started_at = 0.0
            self._last_hover_point = None
            self._last_hover_shape = ""
            self.page.canvas.clear_sam_preview()
            if self._model_loaded:
                self._set_state("ready" if self._image_ready else "model_ready")
            elif self._worker is not None:
                self._set_state("loading_model")
            else:
                self._set_state("disabled")
        self.state_changed.emit()
        return self.enabled


__all__ = ['SamModelStateMixin']
