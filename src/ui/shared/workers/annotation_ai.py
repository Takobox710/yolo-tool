from __future__ import annotations

import json
import sys
import tempfile
from queue import Empty, Queue
from types import SimpleNamespace

from PySide6.QtCore import QThread, Signal

from src.shared.paths import ROOT
from src.services.runtime import spawn_structured_process, stop_process


class AnnotationAiWorker(QThread):
    progress_payload = Signal(object)
    finished_with_result = Signal(object)
    failed = Signal(str)

    def __init__(self, kwargs: dict, _stop_event):
        super().__init__()
        self.kwargs = kwargs
        self._handle = None
        self._stop_requested = False

    def request_stop(self):
        self._stop_requested = True
        stop_process(self._handle)

    def _cli_command(self, flag: str, *args: str) -> list[str]:
        if getattr(sys, "frozen", False):
            return [sys.executable, flag, *args]
        return [sys.executable, "-m", "src.main", flag, *args]

    def _write_payload_file(self, payload: dict) -> str:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", suffix=".json", delete=False
        ) as handle:
            json.dump(payload, handle, ensure_ascii=False)
            return handle.name

    def run(self):
        try:
            queue: Queue = Queue()
            payload_path = self._write_payload_file(self.kwargs)
            self._handle = spawn_structured_process(
                self._cli_command("--yolo-ai-label", payload_path),
                str(ROOT),
                queue,
            )
            result_object = None
            while True:
                try:
                    event, payload = queue.get(timeout=0.1)
                except Empty:
                    continue
                if event == "log":
                    self.progress_payload.emit({"type": "log", "message": str(payload)})
                    continue
                if event == "structured":
                    kind = str(payload.get("event") or "")
                    if kind == "progress":
                        self.progress_payload.emit(dict(payload.get("payload") or {}))
                    elif kind == "done":
                        result_payload = dict(payload.get("result") or {})
                        result_object = SimpleNamespace(**result_payload)
                    elif kind == "error":
                        self.failed.emit(str(payload.get("message") or "AI 预标注失败"))
                        return
                    continue
                if event == "exit":
                    exit_code = int(payload)
                    if exit_code == 0 and result_object is not None:
                        self.finished_with_result.emit(result_object)
                    elif self._stop_requested:
                        self.finished_with_result.emit(
                            SimpleNamespace(
                                processed=0,
                                total=0,
                                updated_images=[],
                                skipped_images=[],
                            )
                        )
                    elif exit_code != 0:
                        self.failed.emit(f"AI 预标注进程结束，退出码：{exit_code}")
                    return
        except Exception as exc:  # pragma: no cover - background safety
            self.failed.emit(str(exc))
        finally:
            self._handle = None


__all__ = ["AnnotationAiWorker"]
