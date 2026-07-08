from __future__ import annotations

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


__all__ = ["Worker"]
