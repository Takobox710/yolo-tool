from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

from src.services.model_export.formats import resolve_export_format
from src.services.model_export.package import load_installed_extension
from src.services.model_export.types import ExportCapability
from src.services.runtime.windows_spawn import hidden_subprocess_kwargs


def _modules_available(modules: tuple[str, ...]) -> bool:
    return all(importlib.util.find_spec(module) is not None for module in modules)


def cuda_available() -> bool:
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        return False
    try:
        result = subprocess.run(
            [nvidia_smi, "-L"],
            capture_output=True,
            text=True,
            timeout=2,
            **hidden_subprocess_kwargs(),
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and bool(result.stdout.strip())


def export_capability(
    export_format: str,
    *,
    frozen: bool | None = None,
    base_root: Path | None = None,
) -> ExportCapability:
    spec = resolve_export_format(export_format)
    is_frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    if spec.built_in:
        if _modules_available(spec.required_modules):
            return ExportCapability(True, "内置运行环境", "运行环境可用")
        missing = ", ".join(spec.required_modules)
        return ExportCapability(False, "内置运行环境", f"缺少依赖：{missing}")

    if not is_frozen and _modules_available(spec.required_modules):
        if spec.argument == "engine" and not cuda_available():
            return ExportCapability(False, "Pixi 开发环境", "TensorRT 需要可用的 NVIDIA GPU。")
        return ExportCapability(True, "Pixi 开发环境", "开发环境依赖可用")

    installed = load_installed_extension(base_root)
    if installed is None or spec.argument not in installed.supported_formats:
        return ExportCapability(False, "独立转换环境", "未安装模型转换环境包。")
    if spec.argument == "engine" and not cuda_available():
        return ExportCapability(False, "独立转换环境", "TensorRT 需要可用的 NVIDIA GPU。")
    return ExportCapability(
        True,
        f"独立转换环境 {installed.version}",
        "运行环境可用",
        None,
    )
