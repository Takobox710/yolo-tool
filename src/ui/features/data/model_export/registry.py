from __future__ import annotations


FORMAT_OPTION_KEYS: dict[str, tuple[str, ...]] = {
    "onnx": ("simplify", "dynamic_onnx", "nms", "opset", "int8"),
    "torchscript": ("dynamic", "nms", "optimize"),
    "openvino": ("dynamic", "nms", "int8"),
    "engine": ("simplify", "dynamic", "nms", "workspace", "int8"),
    "ncnn": (),
}


def option_keys_for(export_format: str) -> tuple[str, ...]:
    return FORMAT_OPTION_KEYS.get(str(export_format).strip().lower(), ())


__all__ = ["FORMAT_OPTION_KEYS", "option_keys_for"]
