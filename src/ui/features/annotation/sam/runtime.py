from __future__ import annotations

import json
import subprocess
import sys
from queue import Empty, Queue
from typing import Any

from PySide6.QtCore import QThread, Signal

from src.services.runtime import (
    spawn_interactive_structured_process,
    stop_process,
)
from src.shared.paths import ROOT


class SamAssistRuntimeWorker(QThread):
    response_received = Signal(str, object, object)
    request_failed = Signal(str, object, str)
    runtime_failed = Signal(str)
    log_received = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._handle = None
        self._runtime_queue: Queue | None = None
        self._command_queue: Queue = Queue()
        self._pending: dict[str, tuple[str, dict[str, Any]]] = {}
        self._request_index = 0
        self._prediction_request_id = ""
        self._latest_prediction: dict[str, Any] | None = None
        self._shutdown_requested = False

    def load_model(self, payload: dict[str, Any]) -> None:
        self._command_queue.put(("load_model", dict(payload)))

    def set_image(self, payload: dict[str, Any]) -> None:
        self._command_queue.put(("set_image", dict(payload)))

    def predict_point(self, payload: dict[str, Any]) -> None:
        self._command_queue.put(("predict_point", dict(payload)))

    def shutdown(self) -> None:
        self._command_queue.put(("shutdown", {}))

    def _cli_command(self) -> list[str]:
        if getattr(sys, "frozen", False):
            return [sys.executable, "--sam-assist-runtime"]
        return [sys.executable, "-m", "src.main", "--sam-assist-runtime"]

    def _ensure_runtime(self) -> None:
        if self._handle is not None and self._handle.process.poll() is None:
            return
        self._runtime_queue = Queue()
        self._handle = spawn_interactive_structured_process(
            self._cli_command(),
            str(ROOT),
            self._runtime_queue,
        )

    def _next_request_id(self, action: str) -> str:
        self._request_index += 1
        return f"sam-{action}-{self._request_index}"

    def _send(self, action: str, payload: dict[str, Any]) -> str:
        self._ensure_runtime()
        if self._handle is None or self._handle.process.stdin is None:
            raise RuntimeError("SAM 智能标注运行时未就绪。")
        request_id = self._next_request_id(action)
        metadata = dict(payload)
        command = dict(payload)
        command.update({"request_id": request_id, "action": action})
        self._pending[request_id] = (action, metadata)
        self._handle.process.stdin.write(json.dumps(command, ensure_ascii=False) + "\n")
        self._handle.process.stdin.flush()
        return request_id

    def _send_latest_prediction(self) -> None:
        if self._prediction_request_id or self._latest_prediction is None:
            return
        payload = self._latest_prediction
        self._latest_prediction = None
        try:
            self._prediction_request_id = self._send("predict_point", payload)
        except Exception as exc:
            self.request_failed.emit("predict_point", payload, str(exc))

    def _handle_command(self, action: str, payload: dict[str, Any]) -> None:
        if action == "shutdown":
            self._shutdown_requested = True
            self._latest_prediction = None
            self._send_shutdown_command()
            stop_process(self._handle)
            return
        if action == "predict_point":
            self._latest_prediction = payload
            self._send_latest_prediction()
            return
        if action in {"load_model", "set_image"}:
            self._latest_prediction = None
            try:
                self._send(action, payload)
            except Exception as exc:
                self.request_failed.emit(action, payload, str(exc))

    def _send_shutdown_command(self) -> None:
        if self._handle is None or self._handle.process.poll() is not None:
            return
        stdin = self._handle.process.stdin
        if stdin is None:
            return
        try:
            request_id = self._next_request_id("shutdown")
            stdin.write(
                json.dumps(
                    {"request_id": request_id, "action": "shutdown"},
                    ensure_ascii=False,
                )
                + "\n"
            )
            stdin.flush()
            self._handle.process.wait(timeout=0.75)
        except (BrokenPipeError, OSError, subprocess.TimeoutExpired):
            return

    def _drain_runtime_events(self) -> None:
        if self._runtime_queue is None:
            return
        while True:
            try:
                event, payload = self._runtime_queue.get_nowait()
            except Empty:
                return
            if event == "log":
                self.log_received.emit(str(payload))
                continue
            if event == "structured":
                self._handle_structured_payload(dict(payload or {}))
                continue
            if event == "exit":
                self._handle_runtime_exit(int(payload))
                return

    def _handle_structured_payload(self, payload: dict[str, Any]) -> None:
        request_id = str(payload.get("request_id") or "")
        pending = self._pending.pop(request_id, None)
        if pending is None:
            return
        action, metadata = pending
        if request_id == self._prediction_request_id:
            self._prediction_request_id = ""
        event = str(payload.get("event") or "")
        if event == "runtime_response":
            self.response_received.emit(action, metadata, dict(payload.get("result") or {}))
        elif event == "runtime_error":
            self.request_failed.emit(
                action,
                metadata,
                str(payload.get("message") or "SAM 智能标注失败。"),
            )
        self._send_latest_prediction()

    def _handle_runtime_exit(self, exit_code: int) -> None:
        self._runtime_queue = None
        self._handle = None
        self._pending.clear()
        self._prediction_request_id = ""
        self._latest_prediction = None
        if exit_code != 0 and not self._shutdown_requested:
            self.runtime_failed.emit(f"SAM 智能标注进程结束，退出码：{exit_code}")

    def run(self) -> None:
        try:
            while not self._shutdown_requested:
                self._drain_runtime_events()
                try:
                    action, payload = self._command_queue.get(timeout=0.05)
                except Empty:
                    continue
                self._handle_command(str(action), dict(payload or {}))
        except Exception as exc:  # pragma: no cover - background safety
            self.runtime_failed.emit(str(exc))
        finally:
            stop_process(self._handle)
            self._handle = None
            self._runtime_queue = None


__all__ = ["SamAssistRuntimeWorker"]
