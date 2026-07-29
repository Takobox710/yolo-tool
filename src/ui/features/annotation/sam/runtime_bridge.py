from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from src.shared.qt import QMessageBox
from src.ui.features.annotation.sam.runtime import SamAssistRuntimeWorker


class SamRuntimeBridgeMixin:

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


    def _worker_finished(self, worker: SamAssistRuntimeWorker) -> None:
        self._workers.discard(worker)
        if self._worker is worker:
            self._worker = None
        worker.deleteLater()


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
        controller_module = sys.modules["src.ui.features.annotation.sam.controller"]
        worker = controller_module.SamAssistRuntimeWorker(self)
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


    def release_for_ai_prelabel(self) -> None:
        if self._worker is None and not self.enabled:
            return
        self.page.append_program_log("AI 预标注启动前已释放画布 SAM 模型与显存。")
        self.shutdown(wait=True)


    def _set_state(self, state: str) -> None:
        self.state = str(state)
        self.page.canvas.sam_state = self.state
        self.page.canvas._notify_canvas_status_changed()
        self.state_changed.emit()


    def _show_error(self, message: str) -> None:
        self.page.append_program_log(f"SAM 智能标注失败：{message}")
        QMessageBox.warning(self.page, "SAM 智能标注", str(message))


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


__all__ = ['SamRuntimeBridgeMixin']
