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
from src.services.runtime.variant import CPU_VARIANT, installed_variant


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
    model_kind: str = "yolo",
    precision: str = "fp32",
    frozen: bool | None = None,
    base_root: Path | None = None,
) -> ExportCapability:
    spec = resolve_export_format(export_format)
    from src.services.model_export.capabilities import capabilities_for, normalize_precision

    normalized_precision = normalize_precision(precision)
    capabilities = capabilities_for(spec.argument, model_kind)
    if normalized_precision not in capabilities.precisions:
        return ExportCapability(
            False,
            "配置能力矩阵",
            f"{spec.display_name} 不支持 {normalized_precision}。",
        )
    if str(model_kind).lower() == "sam2" and spec.argument != "onnx":
        return ExportCapability(False, "配置能力矩阵", "SAM2/SAM2.1 目前只支持 ONNX。")
    is_frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    variant = installed_variant()
    if variant == CPU_VARIANT and spec.argument == "engine":
        return ExportCapability(
            False,
            "CPU 内置运行环境",
            "CPU 版不包含 TensorRT。",
        )
    if spec.argument == "engine" and not cuda_available():
        return ExportCapability(
            False,
            "运行环境",
            "TensorRT 需要可用的 NVIDIA GPU。",
        )
    if spec.argument == "torchscript" and normalized_precision == "fp16" and not cuda_available():
        return ExportCapability(
            False,
            "运行环境",
            "TorchScript FP16 导出需要可用的 NVIDIA GPU。",
        )
    required_modules = spec.required_modules
    if spec.argument == "onnx" and str(model_kind).lower() == "sam2":
        required_modules = (
            "torch",
            "sam2",
            "onnx",
            "onnxslim",
            "onnxscript",
            "onnxruntime",
        )
    if spec.argument == "openvino" and normalized_precision == "int8":
        required_modules = (*required_modules, "nncf")
    if variant == CPU_VARIANT:
        if spec.argument == "engine":
            return ExportCapability(
                False,
                "CPU 内置运行环境",
                "CPU 版不包含 TensorRT。",
            )
        if spec.argument in {"openvino", "ncnn"} and _modules_available(required_modules):
            return ExportCapability(True, "CPU 内置运行环境", "运行环境可用")
        if spec.argument in {"openvino", "ncnn"}:
            return ExportCapability(
                False,
                "CPU 内置运行环境",
                "CPU 版内置转换依赖缺失。",
            )
    if spec.built_in:
        if _modules_available(required_modules):
            return ExportCapability(True, "内置运行环境", "运行环境可用")
        missing = ", ".join(required_modules)
        return ExportCapability(False, "内置运行环境", f"缺少依赖：{missing}")

    if not is_frozen and _modules_available(required_modules):
        return ExportCapability(True, "Pixi 开发环境", "开发环境依赖可用")

    installed = load_installed_extension(base_root)
    if installed is None or spec.argument not in installed.supported_formats:
        return ExportCapability(False, "独立转换环境", "未安装模型转换环境包。")
    if spec.argument == "openvino" and normalized_precision == "int8":
        dependencies = installed.manifest.get("dependencies", {})
        if not isinstance(dependencies, dict) or not any(
            str(key).casefold() == "nncf" for key in dependencies
        ):
            return ExportCapability(
                False,
                "独立转换环境",
                "OpenVINO INT8 需要附加包中的 NNCF。",
            )
    return ExportCapability(
        True,
        f"独立转换环境 {installed.version}",
        "运行环境可用",
        None,
    )
