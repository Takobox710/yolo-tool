from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


TrainingImageSize = tuple[int, int]
_NON_RECTANGULAR_MODEL_MARKERS = (
    "rtdetr",
    "sam",
    "fastsam",
    "yolo-world",
    "yoloworld",
)


@dataclass(frozen=True, slots=True)
class TrainingSizeOptions:
    imgsz: int
    rect: bool


def parse_training_image_size(value: int | str | TrainingImageSize) -> TrainingImageSize:
    if isinstance(value, tuple) and len(value) == 2:
        height, width = value
    elif isinstance(value, int) and not isinstance(value, bool):
        height = width = value
    else:
        text = str(value or "").strip().lower().replace("×", "x")
        parts = [part.strip() for part in text.replace(",", "x").split("x")]
        try:
            if len(parts) == 1:
                height = width = int(parts[0])
            elif len(parts) == 2:
                width, height = (int(part) for part in parts)
            else:
                raise ValueError
        except ValueError as exc:
            raise ValueError("图片尺寸必须是整数，或按宽×高填写，例如 640×384。") from exc
    height, width = int(height), int(width)
    if height < 32 or width < 32 or height % 32 or width % 32:
        raise ValueError("图片尺寸的宽和高都必须是不小于 32 的 32 倍数。")
    return height, width


def format_training_image_size(value: int | str | TrainingImageSize) -> str:
    height, width = parse_training_image_size(value)
    return f"{width}×{height}"


def supports_rectangular_training(model_reference: str | Path | None) -> bool:
    name = Path(str(model_reference or "")).name.lower()
    return not any(marker in name for marker in _NON_RECTANGULAR_MODEL_MARKERS)


def training_size_options(
    model_reference: str | Path | None,
    value: int | str | TrainingImageSize,
) -> TrainingSizeOptions:
    height, width = parse_training_image_size(value)
    rectangular = height != width
    if rectangular and not supports_rectangular_training(model_reference):
        name = Path(str(model_reference or "")).name or "当前模型"
        raise ValueError(f"{name} 不支持矩形批次训练；请选择方形图片尺寸。")
    return TrainingSizeOptions(imgsz=max(height, width), rect=rectangular)


def apply_training_size_options(options: dict, model_reference: str | Path | None) -> dict:
    values = dict(options)
    resolved = training_size_options(model_reference, values.get("imgsz", 640))
    values["imgsz"] = resolved.imgsz
    explicit_rect = bool(values.get("rect", False))
    if explicit_rect and not supports_rectangular_training(model_reference):
        name = Path(str(model_reference or "")).name or "当前模型"
        raise ValueError(f"{name} 不支持矩形批次训练；请选择方形图片尺寸。")
    if resolved.rect or explicit_rect:
        values["rect"] = True
    else:
        values.pop("rect", None)
    return values


__all__ = [
    "TrainingImageSize",
    "TrainingSizeOptions",
    "apply_training_size_options",
    "format_training_image_size",
    "parse_training_image_size",
    "supports_rectangular_training",
    "training_size_options",
]
