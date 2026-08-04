from __future__ import annotations

from dataclasses import replace
from src.services.model_export.types import ExportCapabilities, ModelExportConfig
from src.services.model_export.capability_rules import (
    model_kind_from_path,
    normalize_format as _normalize_format,
    normalize_precision,
)


PRECISIONS = ("fp32", "fp16", "int8")
DEFAULT_NMS_CONF = 0.25
DEFAULT_NMS_IOU = 0.45
DEFAULT_NMS_MAX_DET = 300
DEFAULT_CALIBRATION_SAMPLES = 300
DEFAULT_VALIDATION_SAMPLES = 16


def capabilities_for(
    export_format: str,
    model_kind: str = "yolo",
) -> ExportCapabilities:
    normalized = _normalize_format(export_format)
    kind = str(model_kind or "yolo").strip().lower()
    if normalized == "onnx" and kind == "sam2":
        return ExportCapabilities(
            export_format="onnx",
            model_kind="sam2",
            precisions=("fp32", "fp16"),
            supports_simplify=True,
            supports_calibration=False,
            supports_quantized_validation=False,
            supports_batch=False,
            fixed_imgsz=1024,
            fixed_batch=1,
            reason="SAM2/SAM2.1 固定 1024 x 1024、batch=1、单点提示；当前仅提供 FP32/FP16，暂不提供不稳定的 INT8 交互量化。",
        )
    if normalized == "onnx":
        return ExportCapabilities(
            export_format="onnx",
            model_kind="yolo",
            precisions=PRECISIONS,
            supports_dynamic_batch=True,
            supports_dynamic_height=True,
            supports_dynamic_width=True,
            supports_simplify=True,
            supports_nms=True,
            supports_opset=True,
            supports_calibration=True,
            supports_quantized_validation=True,
        )
    if normalized == "torchscript":
        return ExportCapabilities(
            export_format="torchscript",
            precisions=("fp32", "fp16"),
            supports_batch=True,
            supports_dynamic_batch=True,
            supports_dynamic_height=True,
            supports_dynamic_width=True,
            supports_nms=True,
            supports_optimize=True,
        )
    if normalized == "openvino":
        return ExportCapabilities(
            export_format="openvino",
            precisions=PRECISIONS,
            supports_batch=True,
            supports_dynamic_batch=True,
            supports_dynamic_height=True,
            supports_dynamic_width=True,
            supports_nms=True,
            supports_calibration=True,
        )
    if normalized == "engine":
        return ExportCapabilities(
            export_format="engine",
            precisions=PRECISIONS,
            supports_batch=True,
            supports_dynamic_batch=True,
            supports_dynamic_height=True,
            supports_dynamic_width=True,
            supports_simplify=True,
            supports_nms=True,
            supports_workspace=True,
            supports_calibration=True,
            requires_gpu=True,
        )
    if normalized == "ncnn":
        return ExportCapabilities(
            export_format="ncnn",
            precisions=("fp32", "fp16"),
            supports_batch=True,
        )
    raise ValueError(f"不支持的模型格式：{export_format}")


def normalize_model_export_config(
    config: ModelExportConfig,
    *,
    model_kind: str | None = None,
) -> ModelExportConfig:
    export_format = _normalize_format(config.export_format)
    kind = str(model_kind or model_kind_from_path(config.model_path)).strip().lower()
    precision = normalize_precision(config.precision)
    normalized = replace(config, export_format=export_format, precision=precision)
    capabilities = capabilities_for(export_format, kind)
    if capabilities.fixed_imgsz is not None:
        normalized = replace(normalized, imgsz=capabilities.fixed_imgsz)
    if capabilities.fixed_batch is not None:
        normalized = replace(normalized, batch=capabilities.fixed_batch)
    if kind == "sam2" and export_format == "onnx":
        normalized = replace(
            normalized,
            dynamic_batch=False,
            dynamic_height=False,
            dynamic_width=False,
            nms=False,
            nms_conf=DEFAULT_NMS_CONF,
            nms_iou=DEFAULT_NMS_IOU,
            nms_max_det=DEFAULT_NMS_MAX_DET,
            agnostic_nms=False,
            opset=None,
        )
    if not capabilities.supports_dynamic_batch:
        normalized = replace(normalized, dynamic_batch=False)
    if not capabilities.supports_dynamic_height:
        normalized = replace(normalized, dynamic_height=False)
    if not capabilities.supports_dynamic_width:
        normalized = replace(normalized, dynamic_width=False)
    if not capabilities.supports_simplify:
        normalized = replace(normalized, simplify=False)
    if not capabilities.supports_nms:
        normalized = replace(
            normalized,
            nms=False,
            nms_conf=DEFAULT_NMS_CONF,
            nms_iou=DEFAULT_NMS_IOU,
            nms_max_det=DEFAULT_NMS_MAX_DET,
            agnostic_nms=False,
        )
    if not capabilities.supports_opset:
        normalized = replace(normalized, opset=None)
    if not capabilities.supports_workspace:
        normalized = replace(normalized, workspace=None)
    if not capabilities.supports_optimize:
        normalized = replace(normalized, optimize=False)
    if not capabilities.supports_quantized_validation:
        normalized = replace(normalized, validate_quantized=False)
    if normalized.precision != "int8":
        normalized = replace(normalized, calibration_data="")
    return normalized


def validate_model_export_config(
    config: ModelExportConfig,
    *,
    model_kind: str | None = None,
    strict: bool = True,
) -> ModelExportConfig:
    raw_precision = normalize_precision(config.precision)
    normalized = normalize_model_export_config(config, model_kind=model_kind)
    kind = str(model_kind or model_kind_from_path(normalized.model_path)).strip().lower()
    capabilities = capabilities_for(normalized.export_format, kind)
    if strict:
        _validate_unsupported_raw_options(config, capabilities, raw_precision)
        if capabilities.fixed_batch is not None and int(config.batch) != capabilities.fixed_batch:
            raise ValueError(f"当前模型固定 batch={capabilities.fixed_batch}。")
    if normalized.precision not in capabilities.precisions:
        supported = ", ".join(capabilities.precisions)
        raise ValueError(
            f"{normalized.export_format} 不支持 {normalized.precision.upper()}，可用精度：{supported}。"
        )
    if normalized.batch < 1:
        raise ValueError("batch 必须是不小于 1 的整数。")
    if capabilities.fixed_batch is not None and normalized.batch != capabilities.fixed_batch:
        raise ValueError(f"当前模型固定 batch={capabilities.fixed_batch}。")
    if normalized.imgsz < 32 or normalized.imgsz % 32:
        raise ValueError("输入尺寸必须是不小于 32 的 32 倍数。")
    if not capabilities.supports_batch and normalized.batch != 1:
        raise ValueError("当前格式不支持自定义 batch。")
    for field, enabled, supported in (
        ("dynamic_batch", normalized.dynamic_batch, capabilities.supports_dynamic_batch),
        ("dynamic_height", normalized.dynamic_height, capabilities.supports_dynamic_height),
        ("dynamic_width", normalized.dynamic_width, capabilities.supports_dynamic_width),
    ):
        if enabled and not supported:
            raise ValueError(f"当前格式不支持动态轴：{field}。")
    if normalized.simplify and not capabilities.supports_simplify:
        raise ValueError("当前格式不支持图简化。")
    if normalized.nms and not capabilities.supports_nms:
        raise ValueError("当前格式不支持导出 NMS。")
    if normalized.opset is not None:
        if not capabilities.supports_opset:
            raise ValueError("当前格式不支持自定义 ONNX opset。")
        if not 7 <= int(normalized.opset) <= 21:
            raise ValueError("opset 必须在 7 到 21 之间。")
    if normalized.workspace is not None:
        if not capabilities.supports_workspace:
            raise ValueError("当前格式不支持 TensorRT workspace。")
        if float(normalized.workspace) < 0:
            raise ValueError("TensorRT workspace 不能为负数。")
    if normalized.optimize and not capabilities.supports_optimize:
        raise ValueError("当前格式不支持 TorchScript 优化。")
    if (
        normalized.export_format == "torchscript"
        and normalized.optimize
        and normalized.precision == "fp16"
    ):
        raise ValueError("TorchScript 优化需要 CPU，不能与 FP16 GPU 导出同时启用。")
    if (
        normalized.batch == 1
        and any(dynamic_axes(normalized))
        and (normalized.export_format == "engine" or normalized.nms)
    ):
        raise ValueError("当前动态导出组合要求 batch 大于 1。")
    if normalized.precision == "int8":
        if not capabilities.supports_calibration:
            raise ValueError("当前格式不支持 INT8 静态量化。")
        if not str(normalized.calibration_data or "").strip():
            raise ValueError("启用 INT8 后必须选择校准数据。")
        if normalized.calibration_samples < 1:
            raise ValueError("校准样本数必须大于 0。")
    elif str(normalized.calibration_data or "").strip():
        raise ValueError("只有启用 INT8 时才能设置校准数据。")
    if normalized.validation_samples < 1:
        raise ValueError("验证样本数必须大于 0。")
    if capabilities.supports_nms:
        if not 0 <= float(normalized.nms_conf) <= 1:
            raise ValueError("NMS 置信度必须在 0 到 1 之间。")
        if not 0 <= float(normalized.nms_iou) <= 1:
            raise ValueError("NMS IoU 必须在 0 到 1 之间。")
        if int(normalized.nms_max_det) < 1:
            raise ValueError("NMS 最大检测数必须大于 0。")
    if kind == "sam2" and normalized.export_format != "onnx":
        raise ValueError("SAM2/SAM2.1 目前只支持 ONNX 导出。")
    return normalized


def _validate_unsupported_raw_options(
    config: ModelExportConfig,
    capabilities: ExportCapabilities,
    precision: str,
) -> None:
    for field, enabled, supported in (
        ("dynamic_batch", config.dynamic_batch, capabilities.supports_dynamic_batch),
        ("dynamic_height", config.dynamic_height, capabilities.supports_dynamic_height),
        ("dynamic_width", config.dynamic_width, capabilities.supports_dynamic_width),
    ):
        if enabled and not supported:
            raise ValueError(f"当前格式不支持动态轴：{field}。")
    if config.simplify and not capabilities.supports_simplify:
        raise ValueError("当前格式不支持图简化。")
    if config.nms and not capabilities.supports_nms:
        raise ValueError("当前格式不支持导出 NMS。")
    if config.opset is not None and not capabilities.supports_opset:
        raise ValueError("当前格式不支持自定义 ONNX opset。")
    if config.workspace is not None and not capabilities.supports_workspace:
        raise ValueError("当前格式不支持 TensorRT workspace。")
    if config.optimize and not capabilities.supports_optimize:
        raise ValueError("当前格式不支持 TorchScript 优化。")
    if precision != "int8" and str(config.calibration_data or "").strip():
        raise ValueError("只有启用 INT8 时才能设置校准数据。")


def dynamic_axes(config: ModelExportConfig) -> tuple[bool, bool, bool]:
    return (bool(config.dynamic_batch), bool(config.dynamic_height), bool(config.dynamic_width))


__all__ = [
    "DEFAULT_CALIBRATION_SAMPLES",
    "DEFAULT_NMS_CONF",
    "DEFAULT_NMS_IOU",
    "DEFAULT_NMS_MAX_DET",
    "DEFAULT_VALIDATION_SAMPLES",
    "PRECISIONS",
    "capabilities_for",
    "dynamic_axes",
    "model_kind_from_path",
    "normalize_model_export_config",
    "normalize_precision",
    "validate_model_export_config",
]
