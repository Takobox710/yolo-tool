from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from src.services.model_export.package import (
    PROBE_EXTENSION_ROOT_ENV,
    load_extension_at,
    load_installed_extension,
)
from src.services.model_export.manifest import ORT_GPU_OVERLAY_DIR, ORT_GPU_OVERLAY_KEY
from src.services.model_export.types import InstalledExtension
from src.services.runtime.variant import CPU_VARIANT, installed_variant
from src.services.runtime.windows_spawn import hidden_subprocess_kwargs


_DLL_HANDLES: list[object] = []
ORT_GPU_ROOT_ENV = "YOLO_TOOL_ORT_GPU_ROOT"


def _ort_probe_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--yolo-ort-probe"]
    return [sys.executable, "-m", "src.main", "--yolo-ort-probe"]


def _gpu_ort_available(root: Path) -> bool:
    env = os.environ.copy()
    env[ORT_GPU_ROOT_ENV] = str(root.resolve())
    try:
        result = subprocess.run(
            _ort_probe_command(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            env=env,
            **hidden_subprocess_kwargs(),
        )
    except (OSError, subprocess.SubprocessError):
        return False
    try:
        payload = json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        return False
    return bool(
        result.returncode == 0
        and payload.get("ok")
        and "CUDAExecutionProvider" in payload.get("providers", ())
    )


def activate_installed_extension(base_root: Path | None = None) -> bool:
    if installed_variant() == CPU_VARIANT:
        return False
    candidate_root = os.environ.get(PROBE_EXTENSION_ROOT_ENV, "").strip()
    installed = (
        load_extension_at(Path(candidate_root))
        if candidate_root
        else load_installed_extension(base_root)
    )
    if installed is None:
        return False
    activate_extension(installed)
    return True


def activate_extension(installed: InstalledExtension) -> None:
    package_dir = installed.package_dir.resolve()
    overlays = installed.manifest.get("runtime_overlays", {})
    gpu_relative = (
        overlays.get(ORT_GPU_OVERLAY_KEY) if isinstance(overlays, dict) else None
    )
    gpu_root = package_dir / str(gpu_relative or ORT_GPU_OVERLAY_DIR)
    if gpu_relative and gpu_root.is_dir() and _gpu_ort_available(gpu_root):
        gpu_text = str(gpu_root)
        if gpu_text in sys.path:
            sys.path.remove(gpu_text)
        sys.path.insert(0, gpu_text)
        _add_dll_path(gpu_root / "onnxruntime" / "capi")
    package_text = str(package_dir)
    if package_text not in sys.path:
        sys.path.append(package_text)
    dll_paths: list[str] = []
    for relative in installed.manifest.get("dll_dirs", ()):
        dll_dir = installed.root / Path(str(relative))
        if not dll_dir.is_dir():
            continue
        dll_text = str(dll_dir.resolve())
        dll_paths.append(dll_text)
        _add_dll_path(dll_dir)
    if dll_paths:
        os.environ["PATH"] = os.pathsep.join([*dll_paths, os.environ.get("PATH", "")])


def _add_dll_path(path: Path) -> None:
    if not path.is_dir():
        return
    path_text = str(path.resolve())
    if os.name == "nt" and hasattr(os, "add_dll_directory"):
        _DLL_HANDLES.append(os.add_dll_directory(path_text))
    os.environ["PATH"] = os.pathsep.join([path_text, os.environ.get("PATH", "")])
