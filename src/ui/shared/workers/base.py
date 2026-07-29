from __future__ import annotations

from PySide6.QtCore import QThread, Signal


class Worker(QThread):
    finished_with_payload = Signal(str, object)
    progress = Signal(str, int)
    progress_detail = Signal(object)

    def __init__(self, kind: str, fn, *, accepts_progress: bool = False):
        super().__init__()
        self.kind = kind
        self.fn = fn
        self.accepts_progress = accepts_progress

    def report_progress(self, message: str, value: int, detail=None) -> None:
        self.progress.emit(str(message), max(0, min(100, int(value))))
        if detail is not None:
            self.progress_detail.emit(detail)

    def run(self):
        try:
            payload = self.fn(self.report_progress) if self.accepts_progress else self.fn()
        except Exception as exc:  # pragma: no cover - background safety
            payload = {"error": str(exc)}
        self.finished_with_payload.emit(self.kind, payload)


__all__ = ["Worker"]
