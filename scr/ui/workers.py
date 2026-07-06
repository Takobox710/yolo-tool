from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from queue import Empty, Queue
from types import SimpleNamespace
from typing import Any

from PySide6.QtCore import QThread, Signal

from scr.paths import ROOT
from scr.services.detection_service import DetectionItem
from scr.services.process_utils import hidden_subprocess_kwargs
from scr.services.runtime_service import spawn_structured_process, stop_process


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
        return [sys.executable, "-m", "scr.main", flag, *args]

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
        return [sys.executable, "-m", "scr.main", flag, *args]

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


class ModelLabelsWorker(QThread):
    finished_with_labels = Signal(object)
    failed = Signal(str)

    def __init__(self, model_path: str):
        super().__init__()
        self.model_path = model_path

    def _cli_command(self, flag: str, *args: str) -> list[str]:
        if getattr(sys, "frozen", False):
            return [sys.executable, flag, *args]
        return [sys.executable, "-m", "scr.main", flag, *args]

    def run(self):
        try:
            result = subprocess.run(
                self._cli_command("--yolo-model-labels", self.model_path),
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                **hidden_subprocess_kwargs(),
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or f"模型类别进程退出码：{result.returncode}")
            labels = json.loads(result.stdout or "[]")
            self.finished_with_labels.emit(labels)
        except Exception as exc:  # pragma: no cover - background safety
            self.failed.emit(str(exc))
