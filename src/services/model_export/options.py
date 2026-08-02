from __future__ import annotations

from pathlib import Path
from typing import Any

from src.services.model_export.capabilities import (
    DEFAULT_CALIBRATION_SAMPLES,
    DEFAULT_NMS_CONF,
    DEFAULT_NMS_IOU,
    DEFAULT_NMS_MAX_DET,
    DEFAULT_VALIDATION_SAMPLES,
    _normalize_format,
    model_kind_from_path,
    normalize_precision,
)
from src.services.model_export.types import ModelExportConfig


def config_from_options(
    options: dict[str, Any],
    *,
    model_path: Path,
    output_dir: Path,
) -> ModelExportConfig:
    """Decode the string key/value CLI protocol without backend flags."""

    export_format = _normalize_format(str(options.get("format", "onnx")))
    model_kind = model_kind_from_path(model_path)
    if "quantize" in options or "precision" in options:
        quantize = options.get("quantize", options.get("precision", "32"))
    elif _as_bool(options.get("int8", False), False):
        quantize = "8"
    elif _as_bool(options.get("half", False), False):
        quantize = "16"
    else:
        quantize = "32"
    default_imgsz = 1024 if model_kind == "sam2" else 640
    default_simplify = export_format in {"onnx", "engine"}
    return ModelExportConfig(
        model_path=model_path,
        output_dir=output_dir,
        export_format=export_format,
        imgsz=_as_int(options.get("imgsz", default_imgsz), default_imgsz),
        simplify=_as_bool(options.get("simplify", default_simplify), default_simplify),
        precision=normalize_precision(quantize),
        batch=_as_int(options.get("batch", 1), 1),
        dynamic_batch=_as_bool(options.get("dynamic_batch", False), False),
        dynamic_height=_as_bool(options.get("dynamic_height", False), False),
        dynamic_width=_as_bool(options.get("dynamic_width", False), False),
        nms=_as_bool(options.get("nms", False), False),
        nms_conf=_as_float(options.get("nms_conf", DEFAULT_NMS_CONF), DEFAULT_NMS_CONF),
        nms_iou=_as_float(options.get("nms_iou", DEFAULT_NMS_IOU), DEFAULT_NMS_IOU),
        nms_max_det=_as_int(options.get("nms_max_det", DEFAULT_NMS_MAX_DET), DEFAULT_NMS_MAX_DET),
        agnostic_nms=_as_bool(options.get("agnostic_nms", False), False),
        opset=_optional_int(options.get("opset")),
        workspace=_optional_float(options.get("workspace")),
        optimize=_as_bool(options.get("optimize", False), False),
        calibration_data=str(options.get("calibration_data", "") or "").strip(),
        calibration_samples=_as_int(
            options.get("calibration_samples", DEFAULT_CALIBRATION_SAMPLES),
            DEFAULT_CALIBRATION_SAMPLES,
        ),
        validate_quantized=_as_bool(options.get("validate_quantized", True), True),
        validation_samples=_as_int(
            options.get("validation_samples", DEFAULT_VALIDATION_SAMPLES),
            DEFAULT_VALIDATION_SAMPLES,
        ),
    )


def _as_bool(value: object, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value or "").strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return fallback


def _as_int(value: object, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _as_float(value: object, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _optional_int(value: object) -> int | None:
    if value is None or not str(value).strip():
        return None
    return _as_int(value, 0)


def _optional_float(value: object) -> float | None:
    if value is None or not str(value).strip():
        return None
    return _as_float(value, 0.0)


__all__ = ["config_from_options"]
