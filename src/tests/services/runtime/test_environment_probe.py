import json

import os

import sys

from pathlib import Path

from types import SimpleNamespace

import pytest

def make_image(path: Path, size=(100, 100), color="white"):
    from PIL import Image

    Image.new("RGB", size, color).save(path)


def test_cached_call_reuses_value_until_ttl_expires(monkeypatch):
    from src.services.runtime import cached_call

    now = {"value": 10.0}
    calls = {"count": 0}

    def clock():
        return now["value"]

    def expensive():
        calls["count"] += 1
        return {"count": calls["count"]}

    first = cached_call("unit-test-cache", 5.0, expensive, clock=clock)
    second = cached_call("unit-test-cache", 5.0, expensive, clock=clock)
    now["value"] = 16.0
    third = cached_call("unit-test-cache", 5.0, expensive, clock=clock)

    assert first == {"count": 1}
    assert second == {"count": 1}
    assert third == {"count": 2}


def test_system_status_uses_short_cache_and_nonzero_sampling(monkeypatch):
    from src.services.runtime import environment_probe as environment_service

    calls = {}

    class Mem:
        used = 12 * 1024**3
        total = 32 * 1024**3

    class Disk:
        used = 100 * 1024**3
        total = 200 * 1024**3

    monkeypatch.setattr(environment_service, "cached_call", lambda key, ttl_seconds, loader, clock=None: (calls.setdefault("ttl", ttl_seconds), loader())[1])

    class PsutilStub:
        @staticmethod
        def virtual_memory():
            return Mem()

        @staticmethod
        def disk_usage(_path):
            return Disk()

        @staticmethod
        def cpu_percent(interval=0.0):
            calls["interval"] = interval
            return 7.5

        @staticmethod
        def cpu_count():
            return 32

    monkeypatch.setitem(environment_service._load_system_status.__globals__, "psutil", PsutilStub)
    import builtins
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "psutil":
            return PsutilStub
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    def fake_run(*args, **kwargs):
        calls["creationflags"] = kwargs.get("creationflags")
        return type("R", (), {"returncode": 1, "stdout": ""})()

    monkeypatch.setattr(environment_service.subprocess, "run", fake_run)

    status = environment_service.system_status()

    assert calls["ttl"] == 0.5
    assert calls["interval"] == 0.1
    assert calls["creationflags"] == getattr(environment_service.subprocess, "CREATE_NO_WINDOW", 0)
    assert status["cpu"] == "7.5% / 32核"


def test_torch_cuda_summary_can_use_subprocess_helper(monkeypatch):
    from src.services.runtime import environment_probe as environment_service

    calls = {}

    monkeypatch.setattr(
        environment_service,
        "cached_call",
        lambda key, ttl_seconds, loader, clock=None: (calls.setdefault("args", (key, ttl_seconds)), loader())[1],
    )

    def fake_run(command, **kwargs):
        calls["command"] = command
        calls["creationflags"] = kwargs.get("creationflags")
        return type(
            "R",
            (),
            {
                "returncode": 0,
                "stdout": json.dumps(
                    {"torch": "2.0.0", "cuda": "13.0", "gpu": "Test GPU"},
                    ensure_ascii=False,
                ),
            },
        )()

    monkeypatch.setattr(environment_service.subprocess, "run", fake_run)

    summary = environment_service.torch_cuda_summary(use_subprocess=True)

    assert calls["args"] == ("torch_cuda_summary_subprocess", 60.0)
    assert calls["command"][-1] == "--torch-summary"
    assert calls["creationflags"] == getattr(environment_service.subprocess, "CREATE_NO_WINDOW", 0)
    assert summary == {"torch": "2.0.0", "cuda": "13.0", "gpu": "Test GPU"}


def test_dependency_versions_reports_versions_and_missing_modules(monkeypatch):
    from src.services.runtime import environment_probe as environment_service

    monkeypatch.setattr(
        environment_service,
        "cached_call",
        lambda key, ttl_seconds, loader, clock=None: loader(),
    )

    module_map = {
        "PySide6": object(),
        "ultralytics": object(),
        "cv2": object(),
        "PIL": object(),
        "psutil": None,
    }

    monkeypatch.setattr(
        environment_service.importlib.util,
        "find_spec",
        lambda name: module_map.get(name),
    )

    def fake_version(name):
        versions = {
            "PySide6": "6.10.0",
            "ultralytics": "8.4.80",
            "opencv-python": "4.13.0",
            "Pillow": "12.2.0",
        }
        if name not in versions:
            raise environment_service.metadata.PackageNotFoundError(name)
        return versions[name]

    monkeypatch.setattr(environment_service.metadata, "version", fake_version)

    versions = environment_service.dependency_versions()

    assert versions == {
        "PySide6": "6.10.0",
        "Ultralytics": "8.4.80",
        "OpenCV": "4.13.0",
        "Pillow": "12.2.0",
        "psutil": "未安装",
    }

