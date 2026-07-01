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
            run_prediction(self.config, self.stop_event, self.result_payload.emit)
            self.finished_with_results.emit(True)
        except Exception as exc:  # pragma: no cover - background safety
            self.failed.emit(str(exc))
