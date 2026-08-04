from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from src.services.model_export.calibration_images import load_image_tensor


def smoke_validate_onnx(model_path: str | Path, images: Iterable[str | Path], sample_limit: int, *, default_imgsz: int = 640) -> dict[str, Any]:
    import numpy as np
    import onnxruntime as ort

    sample_limit = int(sample_limit)
    if sample_limit < 1:
        raise ValueError("量化后验证样本数必须大于 0。")
    session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    inputs = session.get_inputs()
    if not inputs:
        raise ValueError("ONNX 模型没有输入。")
    image_paths = tuple(Path(path) for path in images)[:sample_limit]
    if not image_paths:
        raise ValueError("量化后验证没有可用图片。")
    input_info = inputs[0]
    shape = input_info.shape
    if len(shape) < 4:
        raise ValueError("ONNX 模型输入不是 NCHW 图像张量。")
    batch = _runtime_dimension(shape, 0, 1)
    height = _runtime_dimension(shape, 2, default_imgsz)
    width = _runtime_dimension(shape, 3, default_imgsz)
    checked = 0
    output_shapes: list[list[int]] = []
    for path in image_paths:
        outputs = session.run(None, {input_info.name: load_image_tensor(path, height=height, width=width, batch=batch)})
        if not outputs:
            raise ValueError(f"ONNX 模型没有输出：{model_path}")
        for output in outputs:
            array = np.asarray(output)
            if array.ndim == 0 or any(int(value) <= 0 for value in array.shape):
                raise ValueError(f"ONNX 输出形状无效：{model_path}")
            if np.issubdtype(array.dtype, np.floating) and not np.isfinite(array).all():
                raise ValueError(f"ONNX 输出包含非有限数值：{model_path}")
            output_shapes.append([int(value) for value in array.shape])
        checked += 1
    return {"model": str(Path(model_path).resolve()), "samples": checked, "inputs": [item.name for item in inputs], "outputs": output_shapes}


def write_validation_metadata(path: str | Path, payload: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _runtime_dimension(shape: Any, index: int, fallback: int) -> int:
    if index >= len(shape):
        return fallback
    value = shape[index]
    return int(value) if isinstance(value, int) and value > 0 else fallback


__all__ = ["smoke_validate_onnx", "write_validation_metadata"]
