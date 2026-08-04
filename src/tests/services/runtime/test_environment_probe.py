import json

import os

import sys

from types import SimpleNamespace

import pytest

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


def test_module_version_fallback_covers_frozen_build_without_dist_info(monkeypatch):
    from src.services.runtime import environment_probe as environment_service

    monkeypatch.setattr(
        environment_service.importlib,
        "import_module",
        lambda _name: type("Module", (), {"__version__": "8.4.80"})(),
    )
    monkeypatch.setattr(
        environment_service.importlib.util,
        "find_spec",
        lambda _name: object(),
    )
    monkeypatch.setattr(
        environment_service,
        "_detect_distribution_version",
        lambda _distributions: "",
    )

    versions = environment_service._load_dependency_versions()

    assert versions["Ultralytics"] == "8.4.80"
