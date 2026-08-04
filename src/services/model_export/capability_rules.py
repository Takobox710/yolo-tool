from __future__ import annotations

from pathlib import Path

from src.services.annotation.sam_assist import sam_model_spec_from_path


def model_kind_from_path(model_path: str | Path) -> str:
    spec = sam_model_spec_from_path(Path(model_path))
    return "sam2" if spec is not None and spec.runtime_kind == "sam2" else "yolo"


def normalize_precision(value: object) -> str:
    normalized = str(value or "").strip().lower()
    aliases = {
        "32": "fp32",
        "fp32": "fp32",
        "float32": "fp32",
        "16": "fp16",
        "fp16": "fp16",
        "float16": "fp16",
        "8": "int8",
        "int8": "int8",
        "quantized": "int8",
    }
    try:
        return aliases[normalized]
    except KeyError as exc:
        raise ValueError("导出精度必须是 fp32、fp16 或 int8。") from exc


def normalize_format(value: object) -> str:
    normalized = str(value or "").strip().lower()
    aliases = {
        "onnx": "onnx",
        "onnx model": "onnx",
        "sam2_onnx": "onnx",
        "sam2 onnx": "onnx",
        "torchscript": "torchscript",
        "openvino": "openvino",
        "tensorrt": "engine",
        "engine": "engine",
        "ncnn": "ncnn",
    }
    try:
        return aliases[normalized]
    except KeyError as exc:
        raise ValueError(f"不支持的模型格式：{value}") from exc
