from __future__ import annotations

import subprocess
import threading
from dataclasses import dataclass
from queue import Queue


@dataclass
class ProcessHandle:
    process: subprocess.Popen
    thread: threading.Thread


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
    )

    def forward() -> None:
        assert process.stdout is not None
        for line in process.stdout:
            queue.put(("log", line.rstrip()))
        queue.put(("exit", process.wait()))

    thread = threading.Thread(target=forward, daemon=True)
    thread.start()
    return ProcessHandle(process=process, thread=thread)


def stop_process(handle: ProcessHandle | None) -> None:
    if handle is None:
        return
    if handle.process.poll() is None:
        handle.process.terminate()
