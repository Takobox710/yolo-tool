import json

import os

import sys

from pathlib import Path

from types import SimpleNamespace

import pytest

def make_image(path: Path, size=(100, 100), color="white"):
    from PIL import Image

    Image.new("RGB", size, color).save(path)


def test_logged_process_uses_hidden_windows_subprocess(monkeypatch):
    from queue import Queue

    from src.services.runtime import process_runner as runtime_service

    calls = {}

    class FakeStdout:
        def __iter__(self):
            return iter(())

    class FakeProcess:
        stdout = FakeStdout()

        def wait(self):
            return 0

    def fake_popen(command, **kwargs):
        calls["command"] = command
        calls["creationflags"] = kwargs.get("creationflags")
        return FakeProcess()

    monkeypatch.setattr(runtime_service.subprocess, "Popen", fake_popen)

    handle = runtime_service.spawn_logged_process(["demo"], str(Path.cwd()), Queue())
    handle.thread.join(timeout=1)

    assert calls["command"] == ["demo"]
    assert calls["creationflags"] == getattr(runtime_service.subprocess, "CREATE_NO_WINDOW", 0)


def test_sanitize_terminal_line_removes_ansi_sequences():
    from src.services.runtime import sanitize_terminal_line

    raw = "\x1b[K\x1b[34m\x1b[1mtrain: \x1b[0mScanning labels.cache... 91/91 0.0s\r\n"

    assert sanitize_terminal_line(raw) == "train: Scanning labels.cache... 91/91 0.0s"


def test_logged_process_cleans_terminal_escape_sequences(monkeypatch):
    from queue import Queue

    from src.services.runtime import process_runner as runtime_service

    class FakeStdout:
        def __iter__(self):
            return iter(
                (
                    "\x1b[K1/500 640: 5% 1/20 1.1it/s\r\n",
                    "\x1b[34moptimizer:\x1b[0m AdamW(lr=0.002)\n",
                    "\x1b[K\r\n",
                )
            )

    class FakeProcess:
        stdout = FakeStdout()

        def wait(self):
            return 0

    monkeypatch.setattr(runtime_service.subprocess, "Popen", lambda *_args, **_kwargs: FakeProcess())

    queue = Queue()
    handle = runtime_service.spawn_logged_process(["demo"], str(Path.cwd()), queue)
    handle.thread.join(timeout=1)

    assert queue.get(timeout=1) == ("log", "1/500 640: 5% 1/20 1.1it/s")
    assert queue.get(timeout=1) == ("log", "optimizer: AdamW(lr=0.002)")
    assert queue.get(timeout=1) == ("exit", 0)

