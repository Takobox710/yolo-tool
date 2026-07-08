from __future__ import annotations

import json
import sys
from queue import Empty, Queue
from types import SimpleNamespace
from typing import Any

from PySide6.QtCore import QThread, Signal

from src.shared.paths import ROOT
from src.services.runtime import (
    spawn_interactive_structured_process,
    stop_process,
)


class AiRuntimeWorker(QThread):
    model_labels_loaded = Signal(str, object)
    model_labels_failed = Signal(str, str)
    progress_payload = Signal(object)
    finished_with_result = Signal(object)
    failed = Signal(str)

    def __init__(self):
        super().__init__()
        self._handle = None
        self._runtime_queue: Queue | None = None
        self._command_queue: Queue = Queue()
        self._shutdown_requested = False
        self._stop_requested = False
        self._request_index = 0
        self._label_requests: dict[str, str] = {}
        self._ai_request_id = ""

    def _cli_command(self, flag: str, *args: str) -> list[str]:
        if getattr(sys, "frozen", False):
            return [sys.executable, flag, *args]
        return [sys.executable, "-m", "src.main", flag, *args]

    def request_model_labels(self, model_path: str) -> None:
        self._command_queue.put(("load_model_labels", str(model_path)))

    def start_ai_labeling(self, payload: dict) -> None:
        self._command_queue.put(("start_ai_labeling", dict(payload)))

    def request_stop(self) -> None:
        self._command_queue.put(("stop_ai_labeling", None))

    def shutdown(self) -> None:
        self._command_queue.put(("shutdown", None))

    def _next_request_id(self, prefix: str) -> str:
        self._request_index += 1
        return f"{prefix}-{self._request_index}"

    def _ensure_runtime(self) -> None:
        if self._handle is not None and self._handle.process.poll() is None:
            return
        self._runtime_queue = Queue()
        self._handle = spawn_interactive_structured_process(
            self._cli_command("--yolo-ai-runtime"),
            str(ROOT),
            self._runtime_queue,
        )

    def _send_runtime_command(self, payload: dict[str, Any]) -> None:
        self._ensure_runtime()
        if self._handle is None or self._handle.process.stdin is None:
            raise RuntimeError("AI 预标注运行时未就绪。")
        message = json.dumps(payload, ensure_ascii=False) + "\n"
        self._handle.process.stdin.write(message)
        self._handle.process.stdin.flush()

    def _drain_runtime_events(self) -> None:
        if self._runtime_queue is None:
            return
        while True:
            try:
                event, payload = self._runtime_queue.get_nowait()
            except Empty:
                return
            if event == "log":
                if self._ai_request_id:
                    self.progress_payload.emit({"type": "log", "message": str(payload)})
                continue
            if event == "structured":
                self._handle_structured_payload(dict(payload or {}))
                continue
            if event == "exit":
                self._handle_runtime_exit(int(payload))
                return

    def _handle_structured_payload(self, payload: dict[str, Any]) -> None:
        event = str(payload.get("event") or "")
        request_id = str(payload.get("request_id") or "")
        if event == "runtime_progress":
            if request_id == self._ai_request_id:
                self.progress_payload.emit(dict(payload.get("payload") or {}))
            return
        if event == "runtime_response":
            result = dict(payload.get("result") or {})
            if request_id in self._label_requests:
                model_path = self._label_requests.pop(request_id)
                self.model_labels_loaded.emit(model_path, result.get("labels") or [])
                return
            if request_id == self._ai_request_id:
                self._ai_request_id = ""
                self.finished_with_result.emit(
                    SimpleNamespace(
                        processed=int(result.get("processed") or 0),
                        total=int(result.get("total") or 0),
                        updated_images=list(result.get("updated_images") or []),
                        skipped_images=list(result.get("skipped_images") or []),
                    )
                )
            return
        if event == "runtime_error":
            message = str(payload.get("message") or "AI 预标注失败")
            if request_id in self._label_requests:
                model_path = self._label_requests.pop(request_id)
                self.model_labels_failed.emit(model_path, message)
                return
            if request_id == self._ai_request_id:
                self._ai_request_id = ""
                self.failed.emit(message)

    def _handle_runtime_exit(self, exit_code: int) -> None:
        pending_label_requests = dict(self._label_requests)
        active_ai_request = self._ai_request_id
        stop_requested = self._stop_requested
        shutdown_requested = self._shutdown_requested

        self._label_requests.clear()
        self._ai_request_id = ""
        self._stop_requested = False
        self._runtime_queue = None
        self._handle = None

        if stop_requested and active_ai_request:
            self.finished_with_result.emit(
                SimpleNamespace(
                    processed=0,
                    total=0,
                    updated_images=[],
                    skipped_images=[],
                )
            )
            return

        if exit_code != 0 and active_ai_request:
            self.failed.emit(f"AI 预标注进程结束，退出码：{exit_code}")

        if exit_code != 0 and not shutdown_requested:
            for model_path in pending_label_requests.values():
                self.model_labels_failed.emit(
                    model_path,
                    f"模型类别进程结束，退出码：{exit_code}",
                )

    def run(self):
        try:
            while True:
                self._drain_runtime_events()
                if self._shutdown_requested and self._handle is None and self._command_queue.empty():
                    return
                try:
                    command, payload = self._command_queue.get(timeout=0.05)
                except Empty:
                    continue
                if command == "load_model_labels":
                    model_path = str(payload or "").strip()
                    request_id = self._next_request_id("labels")
                    self._label_requests[request_id] = model_path
                    try:
                        self._send_runtime_command(
                            {
                                "request_id": request_id,
                                "action": "load_model_labels",
                                "model_path": model_path,
                            }
                        )
                    except Exception as exc:  # pragma: no cover - background safety
                        self._label_requests.pop(request_id, None)
                        self.model_labels_failed.emit(model_path, str(exc))
                    continue
                if command == "start_ai_labeling":
                    if self._ai_request_id:
                        continue
                    request_id = self._next_request_id("ai")
                    self._ai_request_id = request_id
                    try:
                        self._send_runtime_command(
                            {
                                "request_id": request_id,
                                "action": "apply_ai_labeling",
                                "payload": dict(payload or {}),
                            }
                        )
                    except Exception as exc:  # pragma: no cover - background safety
                        self._ai_request_id = ""
                        self.failed.emit(str(exc))
                    continue
                if command == "stop_ai_labeling":
                    self._stop_requested = bool(self._ai_request_id)
                    stop_process(self._handle)
                    continue
                if command == "shutdown":
                    self._shutdown_requested = True
                    stop_process(self._handle)
        except Exception as exc:  # pragma: no cover - background safety
            self.failed.emit(str(exc))
        finally:
            stop_process(self._handle)
            self._handle = None
            self._runtime_queue = None


__all__ = ["AiRuntimeWorker"]
