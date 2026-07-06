from __future__ import annotations

import threading
from typing import Any, Callable

from PySide6.QtCore import QThread, Signal


class Worker(QThread):
    finished_with_payload = Signal(str, object)

    def __init__(self, kind: str, fn):
        super().__init__()
        self.kind = kind
        self.fn = fn

    def run(self):
        try:
            payload = self.fn()
        except Exception as exc:  # pragma: no cover - background safety
            payload = {"error": str(exc)}
        self.finished_with_payload.emit(self.kind, payload)


class DetectionWorker(QThread):
    progress = Signal(str)
    result_payload = Signal(object)
    finished_with_results = Signal(object)
    failed = Signal(str)

    def __init__(self, config: dict, stop_event: threading.Event):
        super().__init__()
        self.config = config
        self.stop_event = stop_event

    def run(self):
        from scr.services.detection_service import run_prediction

        try:
            self.progress.emit("正在准备检测任务...")
            run_prediction(
                self.config,
                self.stop_event,
                self.result_payload.emit,
                self.progress.emit,
            )
            self.finished_with_results.emit(True)
        except Exception as exc:  # pragma: no cover - background safety
            self.failed.emit(str(exc))


class AnnotationAiWorker(QThread):
    progress_payload = Signal(object)
    finished_with_result = Signal(object)
    failed = Signal(str)

    def __init__(self, kwargs: dict, stop_event: threading.Event):
        super().__init__()
        self.kwargs = kwargs
        self.stop_event = stop_event

    def run(self):
        from scr.services.annotation_ai_service import apply_ai_labeling

        try:
            result = apply_ai_labeling(
                progress_callback=self.progress_payload.emit,
                stop_event=self.stop_event,
                **self.kwargs,
            )
            self.finished_with_result.emit(result)
        except Exception as exc:  # pragma: no cover - background safety
            self.failed.emit(str(exc))


class ModelLabelsWorker(QThread):
    finished_with_labels = Signal(object)
    failed = Signal(str)

    def __init__(self, model_path: str):
        super().__init__()
        self.model_path = model_path

    def run(self):
        from scr.services.annotation_ai_service import load_model_labels

        try:
            labels = load_model_labels(self.model_path)
            self.finished_with_labels.emit(labels)
        except Exception as exc:  # pragma: no cover - background safety
            self.failed.emit(str(exc))
