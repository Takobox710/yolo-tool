from __future__ import annotations

import os
import subprocess
import time
from threading import Event


def launch_installer(path: str | os.PathLike[str]):
    installer = str(os.path.abspath(path))
    if os.name == "nt":
        return subprocess.Popen(
            [installer],
            cwd=os.path.dirname(installer),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    startfile = getattr(os, "startfile", None)
    if callable(startfile):
        startfile(installer)
        return None
    return subprocess.Popen([installer], cwd=os.path.dirname(installer))


def installer_process(process):
    if hasattr(process, "suspend") and hasattr(process, "resume"):
        return process
    if process is None or not getattr(process, "pid", None):
        raise ValueError("安装器进程不可暂停。")
    import psutil

    return psutil.Process(process.pid)


def pause_installer(process) -> None:
    installer_process(process).suspend()


def resume_installer(process) -> None:
    installer_process(process).resume()


def wait_if_paused(pause_event: Event | None, stop_event: Event | None = None) -> None:
    while pause_event is not None and pause_event.is_set():
        if stop_event is not None and stop_event.is_set():
            return
        time.sleep(0.1)


__all__ = ["launch_installer", "pause_installer", "resume_installer", "wait_if_paused"]
