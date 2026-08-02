from __future__ import annotations

import sys
from pathlib import Path

from src.services.model_export.capabilities import (
    capabilities_for,
    dynamic_axes,
    model_kind_from_path,
    validate_model_export_config,
)
from src.services.model_export.formats import resolve_export_format
from src.services.model_export.types import ModelExportConfig


def app_cli_command(*args: str) -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, *args]
    return [sys.executable, "-m", "src.main", *args]


def build_model_export_command(
    config: ModelExportConfig,
    *,
    runtime_executable: Path | None = None,
) -> list[str]:
    config = validate_model_export_config(config)
    spec = resolve_export_format(config.export_format)
    capabilities = capabilities_for(
        spec.argument,
        model_kind_from_path(config.model_path),
    )
    quantize = {"fp32": 32, "fp16": 16, "int8": 8}[config.precision]
    prefix = (
        [str(runtime_executable), "--yolo-export"]
        if runtime_executable is not None
        else app_cli_command("--yolo-export")
    )
    command = [
        *prefix,
        f"model={config.model_path}",
        f"format={spec.argument}",
        f"imgsz={int(config.imgsz)}",
        f"quantize={quantize}",
        f"output_dir={config.output_dir}",
    ]
    if capabilities.supports_batch:
        command.append(f"batch={int(config.batch)}")
    batch_dynamic, height_dynamic, width_dynamic = dynamic_axes(config)
    if capabilities.supports_dynamic_batch:
        command.append(f"dynamic_batch={str(batch_dynamic).lower()}")
    if capabilities.supports_dynamic_height:
        command.append(f"dynamic_height={str(height_dynamic).lower()}")
    if capabilities.supports_dynamic_width:
        command.append(f"dynamic_width={str(width_dynamic).lower()}")
    if capabilities.supports_simplify:
        command.append(f"simplify={str(bool(config.simplify)).lower()}")
    if capabilities.supports_nms:
        command.extend(
            [
                f"nms={str(bool(config.nms)).lower()}",
                f"nms_conf={float(config.nms_conf)}",
                f"nms_iou={float(config.nms_iou)}",
                f"nms_max_det={int(config.nms_max_det)}",
                f"agnostic_nms={str(bool(config.agnostic_nms)).lower()}",
            ]
        )
    if capabilities.supports_opset and config.opset is not None:
        command.append(f"opset={int(config.opset)}")
    if capabilities.supports_workspace and config.workspace is not None:
        command.append(f"workspace={float(config.workspace)}")
    if capabilities.supports_optimize:
        command.append(f"optimize={str(bool(config.optimize)).lower()}")
    if config.precision == "int8" and capabilities.supports_calibration:
        command.extend(
            [
                f"calibration_data={config.calibration_data}",
                f"calibration_samples={int(config.calibration_samples)}",
            ]
        )
        if capabilities.supports_quantized_validation:
            command.extend(
                [
                    f"validate_quantized={str(bool(config.validate_quantized)).lower()}",
                    f"validation_samples={int(config.validation_samples)}",
                ]
            )
    return command


def build_export_command(
    model_path: str,
    export_format: str,
    imgsz: int | str = 640,
) -> list[str]:
    spec = resolve_export_format(export_format)
    return build_model_export_command(
        ModelExportConfig(
            model_path=Path(model_path),
            output_dir=Path(model_path).resolve().parent,
            export_format=spec.argument,
            imgsz=int(imgsz),
            simplify=spec.argument in {"onnx", "engine"},
        )
    )
