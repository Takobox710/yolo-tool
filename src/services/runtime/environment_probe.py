from __future__ import annotations

import json
import importlib.util
import shutil
import subprocess
import sys
import time
from importlib import metadata
from pathlib import Path
from typing import Callable, TypeVar

from src import APP_VERSION
from src.services.runtime.release_manifest import installed_runtime_version
from src.services.runtime.windows_spawn import hidden_subprocess_kwargs


T = TypeVar("T")
_CACHE: dict[str, tuple[float, object]] = {}
PACKAGE_SPECS: dict[str, dict[str, tuple[str, ...] | str]] = {
    "PySide6": {
        "module": "PySide6",
        "distributions": ("PySide6",),
    },
    "Ultralytics": {
        "module": "ultralytics",
        "distributions": ("ultralytics",),
    },
    "OpenCV": {
        "module": "cv2",
        "distributions": ("opencv-python", "opencv-python-headless"),
    },
    "Pillow": {
        "module": "PIL",
        "distributions": ("Pillow",),
    },
    "psutil": {
        "module": "psutil",
        "distributions": ("psutil",),
    },
}


def cached_call(key: str, ttl_seconds: float, loader: Callable[[], T], clock: Callable[[], float] = time.monotonic) -> T:
    now = clock()
    cached = _CACHE.get(key)
    if cached is not None:
        timestamp, value = cached
        if now - timestamp < ttl_seconds:
            return value  # type: ignore[return-value]
    value = loader()
    _CACHE[key] = (now, value)
    return value


def detect_modules() -> dict[str, bool]:
    return {
        str(spec["module"]): importlib.util.find_spec(str(spec["module"])) is not None
        for spec in PACKAGE_SPECS.values()
    }


def python_version() -> str:
    return sys.version.split()[0]


def application_version() -> str:
    return APP_VERSION


def runtime_version() -> str:
    return installed_runtime_version()


def dependency_versions() -> dict[str, str]:
    return cached_call("dependency_versions", 60.0, _load_dependency_versions)


def pixi_available() -> bool:
    return shutil.which("pixi") is not None


def _load_dependency_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for label, spec in PACKAGE_SPECS.items():
        module_name = str(spec["module"])
        if importlib.util.find_spec(module_name) is None:
            versions[label] = "未安装"
            continue
        version = _detect_distribution_version(tuple(spec["distributions"]))
        versions[label] = version or "已安装"
    return versions


def _detect_distribution_version(distributions: tuple[str, ...]) -> str:
    for distribution in distributions:
        try:
            return metadata.version(distribution)
        except metadata.PackageNotFoundError:
            continue
    return ""


def torch_cuda_summary(*, use_subprocess: bool = False) -> dict[str, str]:
    cache_key = (
        "torch_cuda_summary_subprocess"
        if use_subprocess
        else "torch_cuda_summary_in_process"
    )
    loader = (
        _load_torch_cuda_summary_subprocess
        if use_subprocess
        else _load_torch_cuda_summary_in_process
    )
    return cached_call(cache_key, 60.0, loader)


def preload_torch_runtime() -> dict[str, str]:
    return torch_cuda_summary(use_subprocess=False)


def _load_torch_cuda_summary_in_process() -> dict[str, str]:
    try:
        import torch

        return {
            "torch": getattr(torch, "__version__", "未知"),
            "cuda": str(getattr(torch.version, "cuda", "未知")),
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "不可用",
        }
    except Exception:
        return {"torch": "未安装", "cuda": "未知", "gpu": "不可用"}


def _torch_summary_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--torch-summary"]
    return [sys.executable, "-m", "src.main", "--torch-summary"]


def _load_torch_cuda_summary_subprocess() -> dict[str, str]:
    try:
        result = subprocess.run(
            _torch_summary_command(),
            capture_output=True,
            text=True,
            timeout=30,
            **hidden_subprocess_kwargs(),
        )
    except Exception:
        return {"torch": "未安装", "cuda": "未知", "gpu": "不可用"}
    if result.returncode != 0:
        return {"torch": "未安装", "cuda": "未知", "gpu": "不可用"}
    try:
        payload = json.loads(result.stdout.strip() or "{}")
    except json.JSONDecodeError:
        return {"torch": "未安装", "cuda": "未知", "gpu": "不可用"}
    return {
        "torch": str(payload.get("torch", "未知")),
        "cuda": str(payload.get("cuda", "未知")),
        "gpu": str(payload.get("gpu", "不可用")),
    }


def system_status() -> dict[str, str]:
    return cached_call("system_status", 0.5, _load_system_status)


def _load_system_status() -> dict[str, str]:
    status = {"gpu": "未检测", "gpu_usage": "待接入", "vram": "待检测", "cpu": "待检测", "memory": "待检测", "disk": "待检测"}
    try:
        import psutil

        memory = psutil.virtual_memory()
        disk = psutil.disk_usage(str(Path.cwd().anchor or "."))
        status["cpu"] = f"{psutil.cpu_percent(interval=0.1):.1f}% / {psutil.cpu_count()}核"
        status["memory"] = f"{memory.used / 1024**3:.1f}GB / {memory.total / 1024**3:.1f}GB"
        status["disk"] = f"{disk.used / 1024**3:.1f}GB / {disk.total / 1024**3:.1f}GB"
    except Exception:
        pass
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=2,
            **hidden_subprocess_kwargs(),
        )
        if result.returncode == 0 and result.stdout.strip():
            name, usage, used, total = [part.strip() for part in result.stdout.splitlines()[0].split(",")]
            status["gpu"] = name
            status["gpu_usage"] = f"{usage}%"
            status["vram"] = f"{float(used) / 1024:.1f}GB / {float(total) / 1024:.1f}GB"
    except Exception:
        pass
    return status

