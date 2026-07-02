from __future__ import annotations

import importlib.util
import shutil
import subprocess
import time
from pathlib import Path
from typing import Callable, TypeVar

from scr.services.process_utils import hidden_subprocess_kwargs


T = TypeVar("T")
_CACHE: dict[str, tuple[float, object]] = {}


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
    return {name: importlib.util.find_spec(name) is not None for name in ("PySide6", "ultralytics", "cv2", "PIL", "psutil")}


def pixi_available() -> bool:
    return shutil.which("pixi") is not None


def torch_cuda_summary() -> dict[str, str]:
    return cached_call("torch_cuda_summary", 60.0, _load_torch_cuda_summary)


def _load_torch_cuda_summary() -> dict[str, str]:
    try:
        import torch

        return {
            "torch": getattr(torch, "__version__", "未知"),
            "cuda": str(getattr(torch.version, "cuda", "未知")),
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "不可用",
        }
    except Exception:
        return {"torch": "未安装", "cuda": "未知", "gpu": "不可用"}


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
