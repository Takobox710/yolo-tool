from __future__ import annotations

import time
from math import hypot
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal

from src.services.annotation import (
    SamModelSpec,
    find_sam_model_specs,
    preferred_sam_model,
)
from src.shared.qt import QMessageBox
from src.ui.features.annotation.sam.runtime import SamAssistRuntimeWorker


class SamAssistController(QObject):
    state_changed = Signal()

    _HOVER_MIN_INTERVAL_MS = 50
    _HOVER_MAX_INTERVAL_MS = 120
    _HOVER_DEFAULT_INTERVAL_MS = 80
    _HOVER_EMA_ALPHA = 0.35
    _HOVER_MIN_MOVE_PX = 2.0

    def __init__(self, page) -> None:
        super().__init__(page)
        self.page = page
        self.enabled = False
        self.state = "disabled"
        self.models: list[SamModelSpec] = []
        self.selected_model: SamModelSpec | None = None
        self.model_generation = 0
        self.image_generation = 0
        self.hover_generation = 0
        self._minimum_hover_generation = 0
        self._worker: SamAssistRuntimeWorker | None = None
        self._workers: set[SamAssistRuntimeWorker] = set()
        self._model_loaded = False
        self._image_ready = False
        self._hover_payload: dict[str, Any] | None = None
        self._hover_inflight = False
        self._hover_started_at = 0.0
        self._last_hover_submit_at = 0.0
        self._hover_ema_ms: float | None = None
        self._last_hover_point: tuple[float, float] | None = None
        self._last_hover_shape = ""
        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.setInterval(self._HOVER_DEFAULT_INTERVAL_MS)
        self._hover_timer.timeout.connect(self._submit_hover)
        self.refresh_models()
        self.page.canvas.sam_hover_callback = self.request_hover
        self.page.canvas.sam_toggle_callback = self.set_enabled
        self.page.canvas.sam_image_callback = self.set_current_image
        self.page.canvas.sam_cancel_hover_callback = self.cancel_hover

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

    def _load_selected_model(self) -> None:
        if self.selected_model is None:
            return
        self._hover_timer.stop()
        self._hover_payload = None
        self._hover_inflight = False
        self._hover_started_at = 0.0
        self._last_hover_submit_at = 0.0
        self._hover_ema_ms = None
        self._last_hover_point = None
        self._last_hover_shape = ""
        self.page.canvas.clear_sam_preview()
        self._stop_worker(wait=False)
        self._model_loaded = False
        self._image_ready = False
        self.model_generation += 1
        self.image_generation += 1
        self.hover_generation += 1
        self._minimum_hover_generation = self.hover_generation
        worker = SamAssistRuntimeWorker(self)
        worker.response_received.connect(self._handle_response)
        worker.request_failed.connect(self._handle_request_failure)
        worker.runtime_failed.connect(
            lambda message, worker=worker, generation=self.model_generation: (
                self._handle_runtime_failure(
                    message,
                    worker=worker,
                    model_generation=generation,
                )
            )
        )
        worker.log_received.connect(self.page.append_program_log)
        worker.finished.connect(lambda worker=worker: self._worker_finished(worker))
        self._worker = worker
        self._workers.add(worker)
        worker.start()
        self._set_state("loading_model")
        worker.load_model(
            {
                "checkpoint_path": str(self.selected_model.checkpoint_path),
                "config_name": self.selected_model.config_name,
                "runtime_kind": self.selected_model.runtime_kind,
                "model_generation": self.model_generation,
            }
        )

    def set_current_image(self, image_path: Path | None) -> None:
        self.image_generation += 1
        self.hover_generation += 1
        self._minimum_hover_generation = self.hover_generation
        self._hover_timer.stop()
        self._hover_payload = None
        self._image_ready = False
        self._last_hover_point = None
        self._last_hover_shape = ""
        self.page.canvas.clear_sam_preview()
        if not self.enabled:
            return
        if image_path is None:
            self._set_state("waiting_image")
            return
        if self.state not in {"model_ready", "ready", "predicting", "encoding_image"}:
            return
        self._encode_image(image_path)

    def _encode_image(self, image_path: Path) -> None:
        if self._worker is None:
            return
        self._set_state("encoding_image")
        self._worker.set_image(
            {
                "image_path": str(Path(image_path).resolve()),
                "model_generation": self.model_generation,
                "image_generation": self.image_generation,
            }
        )

    def request_hover(self, point: tuple[float, float], shape: str) -> None:
        if not self.enabled or self.state not in {"ready", "predicting"}:
            return
        point = (float(point[0]), float(point[1]))
        shape = str(shape)
        if self._last_hover_point is not None and shape == self._last_hover_shape:
            distance = hypot(
                point[0] - self._last_hover_point[0],
                point[1] - self._last_hover_point[1],
            )
            if distance < self._HOVER_MIN_MOVE_PX:
                return
        self.hover_generation += 1
        self._last_hover_point = point
        self._last_hover_shape = shape
        self._hover_payload = {
            "x": point[0],
            "y": point[1],
            "shape": shape,
            "hover_generation": self.hover_generation,
            "model_generation": self.model_generation,
            "image_generation": self.image_generation,
            **self.parameters(),
        }
        self._hover_payload["simplification_ratio"] = self._hover_payload.pop(
            "polygon_simplification_ratio"
        )
        if not self._hover_inflight and not self._hover_timer.isActive():
            self._submit_hover()

    def cancel_hover(self) -> None:
        self.hover_generation += 1
        self._minimum_hover_generation = self.hover_generation
        self._hover_timer.stop()
        self._hover_payload = None
        self._last_hover_point = None
        self._last_hover_shape = ""
        if self.enabled and self.state == "predicting":
            self._set_state("ready")

    def _submit_hover(self) -> None:
        if (
            self._worker is None
            or self._hover_payload is None
            or not self.enabled
            or self._hover_inflight
        ):
            return
        payload = self._hover_payload
        self._hover_payload = None
        self._hover_timer.stop()
        self._hover_inflight = True
        self._hover_started_at = time.monotonic()
        self._last_hover_submit_at = self._hover_started_at
        self._set_state("predicting")
        self._worker.predict_point(payload)

    def _hover_interval_ms(self) -> int:
        """Return a bounded interval derived from recent SAM latency."""
        if self._hover_ema_ms is None:
            return self._HOVER_DEFAULT_INTERVAL_MS
        interval = int(round(self._hover_ema_ms * 0.75))
        return max(self._HOVER_MIN_INTERVAL_MS, min(self._HOVER_MAX_INTERVAL_MS, interval))

    def _schedule_latest_hover(self) -> None:
        if not self.enabled or self._hover_payload is None or self._hover_inflight:
            return
        elapsed_ms = (time.monotonic() - self._last_hover_submit_at) * 1000.0
        delay_ms = max(0.0, self._hover_interval_ms() - elapsed_ms)
        if delay_ms <= 0:
            self._submit_hover()
        else:
            self._hover_timer.start(max(1, int(delay_ms + 0.5)))

    def _finish_hover_request(self, *, keep_predicting: bool = False) -> None:
        if self._hover_inflight:
            elapsed_ms = max(0.0, (time.monotonic() - self._hover_started_at) * 1000.0)
            if self._hover_ema_ms is None:
                self._hover_ema_ms = elapsed_ms
            else:
                alpha = self._HOVER_EMA_ALPHA
                self._hover_ema_ms = (alpha * elapsed_ms) + ((1.0 - alpha) * self._hover_ema_ms)
            self._hover_inflight = False
            self._hover_started_at = 0.0
        if self._hover_payload is not None:
            self._schedule_latest_hover()
        elif self.enabled and self.state == "predicting" and not keep_predicting:
            self._set_state("ready")

    def _handle_response(
        self,
        action: str,
        metadata: dict[str, Any],
        result: dict[str, Any],
    ) -> None:
        if int(metadata.get("model_generation") or 0) != self.model_generation:
            return
        if action == "load_model":
            self._model_loaded = True
            self._set_state("model_ready")
            if str(result.get("device") or "") == "cpu":
                self.page.append_program_log("SAM 未检测到 CUDA，将使用 CPU，悬停预览可能较慢。")
            if self.enabled and self.page.current_image_path is not None:
                self._encode_image(self.page.current_image_path)
            elif self.enabled:
                self._set_state("waiting_image")
            return
        if action == "set_image":
            if int(metadata.get("image_generation") or 0) != self.image_generation:
                return
            self._image_ready = True
            self._set_state("ready")
            return
        if not self.enabled:
            return
        if action == "predict_point":
            keep_predicting = False
            try:
                if int(metadata.get("image_generation") or 0) != self.image_generation:
                    return
                hover_generation = int(metadata.get("hover_generation") or 0)
                keep_predicting = hover_generation < self.hover_generation
                if hover_generation <= self._minimum_hover_generation:
                    return
                if hover_generation <= self.page.canvas.sam_preview_generation:
                    return
                if str(metadata.get("shape") or "") != self.page.canvas.draw_shape:
                    return
                geometry = result.get("geometry")
                if isinstance(geometry, dict):
                    self.page.canvas.set_sam_preview(
                        str(metadata["shape"]),
                        geometry,
                        hover_generation,
                    )
                else:
                    self.page.canvas.clear_sam_preview()
                self._set_state(
                    "ready" if hover_generation >= self.hover_generation else "predicting"
                )
            finally:
                self._finish_hover_request(keep_predicting=keep_predicting)

    def _handle_request_failure(
        self,
        action: str,
        metadata: dict[str, Any],
        message: str,
    ) -> None:
        if int(metadata.get("model_generation") or 0) != self.model_generation:
            return
        if action == "load_model":
            self._handle_runtime_failure(message)
            return
        if not self.enabled:
            return
        if action == "predict_point":
            keep_predicting = False
            try:
                if int(metadata.get("image_generation") or 0) != self.image_generation:
                    return
                hover_generation = int(metadata.get("hover_generation") or 0)
                keep_predicting = hover_generation < self.hover_generation
                if hover_generation <= self._minimum_hover_generation:
                    return
                if hover_generation >= self.hover_generation:
                    self.page.canvas.clear_sam_preview()
                    self._set_state("ready")
                else:
                    self._set_state("predicting")
                self.page.append_program_log(f"SAM 悬停推理失败：{message}")
            finally:
                self._finish_hover_request(keep_predicting=keep_predicting)
            return
        self._handle_runtime_failure(message)

    def _handle_runtime_failure(
        self,
        message: str,
        *,
        worker: SamAssistRuntimeWorker | None = None,
        model_generation: int | None = None,
    ) -> None:
        if worker is not None and worker is not self._worker:
            return
        if model_generation is not None and model_generation != self.model_generation:
            return
        was_enabled = self.enabled
        self.enabled = False
        self._model_loaded = False
        self._image_ready = False
        self.page.canvas.set_sam_assist_enabled(False)
        self._set_state("error" if was_enabled else "disabled")
        self._stop_worker(wait=False)
        if was_enabled:
            self._show_error(message)
        else:
            self.page.append_program_log(f"SAM 智能标注运行时失败：{message}")
        self.state_changed.emit()

    def _show_error(self, message: str) -> None:
        self.page.append_program_log(f"SAM 智能标注失败：{message}")
        QMessageBox.warning(self.page, "SAM 智能标注", str(message))

    def _set_state(self, state: str) -> None:
        self.state = str(state)
        self.page.canvas.sam_state = self.state
        self.page.canvas._notify_canvas_status_changed()
        self.state_changed.emit()

    def _stop_worker(self, *, wait: bool) -> None:
        worker = self._worker
        self._worker = None
        self._model_loaded = False
        self._image_ready = False
        if worker is None:
            return
        worker.shutdown()
        if wait:
            worker.wait(3000)

    def _worker_finished(self, worker: SamAssistRuntimeWorker) -> None:
        self._workers.discard(worker)
        if self._worker is worker:
            self._worker = None
        worker.deleteLater()

    def shutdown(self, *, wait: bool = True) -> None:
        self.enabled = False
        self._model_loaded = False
        self._image_ready = False
        self._hover_timer.stop()
        self._hover_payload = None
        self.page.canvas.set_sam_assist_enabled(False)
        self._stop_worker(wait=wait)
        if wait:
            for worker in tuple(self._workers):
                worker.shutdown()
                worker.wait(3000)
        self._set_state("disabled")

    def release_for_ai_prelabel(self) -> None:
        if self._worker is None and not self.enabled:
            return
        self.page.append_program_log("AI 预标注启动前已释放画布 SAM 模型与显存。")
        self.shutdown(wait=True)


__all__ = ["SamAssistController"]
