from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time
from dataclasses import dataclass
from queue import Queue

from scr.services.process_utils import hidden_subprocess_kwargs

try:
    import psutil
except ImportError:  # pragma: no cover - optional at runtime
    psutil = None


@dataclass
class ProcessHandle:
    process: subprocess.Popen
    thread: threading.Thread


_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
STRUCTURED_OUTPUT_PREFIX = "__YOLO_JSON__:"


def sanitize_terminal_line(raw: str) -> str:
    text = str(raw).replace("\r", "")
    text = _ANSI_ESCAPE_RE.sub("", text)
    text = _CONTROL_CHAR_RE.sub("", text)
    return text.rstrip("\n")


def spawn_logged_process(command: list[str], cwd: str, queue: Queue) -> ProcessHandle:
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        **hidden_subprocess_kwargs(),
    )

    def forward() -> None:
        assert process.stdout is not None
        try:
            for line in process.stdout:
                cleaned = sanitize_terminal_line(line)
                if cleaned:
                    queue.put(("log", cleaned))
        finally:
            queue.put(("exit", process.wait()))

    thread = threading.Thread(target=forward, daemon=True)
    thread.start()
    return ProcessHandle(process=process, thread=thread)


def spawn_structured_process(command: list[str], cwd: str, queue: Queue) -> ProcessHandle:
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        **hidden_subprocess_kwargs(),
    )

    def forward() -> None:
        assert process.stdout is not None
        try:
            for line in process.stdout:
                cleaned = sanitize_terminal_line(line)
                if not cleaned:
                    continue
                if cleaned.startswith(STRUCTURED_OUTPUT_PREFIX):
                    raw_payload = cleaned[len(STRUCTURED_OUTPUT_PREFIX) :]
                    try:
                        payload = json.loads(raw_payload)
                    except json.JSONDecodeError:
                        queue.put(("log", cleaned))
                        continue
                    queue.put(("structured", payload))
                    continue
                queue.put(("log", cleaned))
        finally:
            queue.put(("exit", process.wait()))

    thread = threading.Thread(target=forward, daemon=True)
    thread.start()
    return ProcessHandle(process=process, thread=thread)


def spawn_interactive_structured_process(
    command: list[str], cwd: str, queue: Queue
) -> ProcessHandle:
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        **hidden_subprocess_kwargs(),
    )

    def forward() -> None:
        assert process.stdout is not None
        try:
            for line in process.stdout:
                cleaned = sanitize_terminal_line(line)
                if not cleaned:
                    continue
                if cleaned.startswith(STRUCTURED_OUTPUT_PREFIX):
                    raw_payload = cleaned[len(STRUCTURED_OUTPUT_PREFIX) :]
                    try:
                        payload = json.loads(raw_payload)
                    except json.JSONDecodeError:
                        queue.put(("log", cleaned))
                        continue
                    queue.put(("structured", payload))
                    continue
                queue.put(("log", cleaned))
        finally:
            queue.put(("exit", process.wait()))

    thread = threading.Thread(target=forward, daemon=True)
    thread.start()
    return ProcessHandle(process=process, thread=thread)


def _wait_for_process_exit(process: subprocess.Popen, timeout_seconds: float) -> bool:
    try:
        process.wait(timeout=timeout_seconds)
        return True
    except subprocess.TimeoutExpired:
        return False


def _stop_process_tree_windows(handle: ProcessHandle, timeout_seconds: float) -> bool:
    if psutil is None:
        return False
    try:
        root = psutil.Process(handle.process.pid)
    except (psutil.Error, ProcessLookupError):
        return handle.process.poll() is not None

    children = root.children(recursive=True)
    for child in reversed(children):
        try:
            child.terminate()
        except psutil.Error:
            continue

    _, alive_children = psutil.wait_procs(children, timeout=max(0.1, timeout_seconds / 2))
    for child in alive_children:
        try:
            child.kill()
        except psutil.Error:
            continue

    try:
        root.terminate()
    except psutil.Error:
        return handle.process.poll() is not None

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if handle.process.poll() is not None:
            return True
        time.sleep(0.05)

    try:
        root.kill()
    except psutil.Error:
        pass
    return _wait_for_process_exit(handle.process, 1.0)


def stop_process(handle: ProcessHandle | None) -> None:
    if handle is None:
        return
    if handle.process.poll() is not None:
        return
    if os.name == "nt" and _stop_process_tree_windows(handle, 2.0):
        return
    handle.process.terminate()
    if _wait_for_process_exit(handle.process, 2.0):
        return
    handle.process.kill()
