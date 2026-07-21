from __future__ import annotations

import json
import sys
import tempfile
from queue import Empty, Queue

from PySide6.QtCore import QThread, Signal

from src.shared.paths import ROOT
from src.services.runtime import spawn_structured_process, stop_process
from src.services.validation import DetectionItem


class DetectionWorker(QThread):
    progress = Signal(str)
    video_progress = Signal(object)
    video_completed = Signal(object)
    result_payload = Signal(object)
    finished_with_results = Signal(object)
    failed = Signal(str)

    def __init__(self, config: dict, _stop_event):
        super().__init__()
        self.config = config
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

    def _deserialize_result_payload(self, payload: dict) -> dict:
        result = dict(payload)
        items = []
        for item in payload.get("items", []):
            points = [tuple(point) for point in item.get("points", [])]
            items.append(
                DetectionItem(
                    label=str(item.get("label", "")),
                    confidence=float(item.get("confidence", 0.0)),
                    center_x=float(item.get("center_x", 0.0)),
                    center_y=float(item.get("center_y", 0.0)),
                    width=float(item.get("width", 0.0)),
                    height=float(item.get("height", 0.0)),
                    angle=float(item.get("angle", 0.0)),
                    points=points,
                )
            )
        result["items"] = items
        return result

    def run(self):
        try:
            self.progress.emit("正在准备检测任务...")
            queue: Queue = Queue()
            payload_path = self._write_payload_file(self.config)
            self._handle = spawn_structured_process(
                self._cli_command("--yolo-predict", payload_path),
                str(ROOT),
                queue,
            )
            while True:
                try:
                    event, payload = queue.get(timeout=0.1)
                except Empty:
                    continue
                if event == "log":
                    self.progress.emit(str(payload))
                    continue
                if event == "structured":
                    kind = str(payload.get("event") or "")
                    if kind == "progress":
                        self.progress.emit(str(payload.get("message") or ""))
                    elif kind == "video_progress":
                        self.video_progress.emit(dict(payload.get("payload") or {}))
                    elif kind == "video_completed":
                        self.video_completed.emit(dict(payload.get("payload") or {}))
                    elif kind == "result":
                        self.result_payload.emit(
                            self._deserialize_result_payload(
                                dict(payload.get("payload") or {})
                            )
                        )
                    elif kind == "error":
                        self.failed.emit(str(payload.get("message") or "检测失败"))
                        return
                    continue
                if event == "exit":
                    exit_code = int(payload)
                    if exit_code == 0 or self._stop_requested:
                        self.finished_with_results.emit(True)
                    else:
                        self.failed.emit(f"检测进程结束，退出码：{exit_code}")
                    return
        except Exception as exc:  # pragma: no cover - background safety
            self.failed.emit(str(exc))
        finally:
            self._handle = None


__all__ = ["DetectionWorker"]
