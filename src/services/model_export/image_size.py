from __future__ import annotations

from typing import TypeAlias


ImageSize: TypeAlias = tuple[int, int]
ImageSizeValue: TypeAlias = ImageSize | int | str


def parse_image_size(value: ImageSizeValue, *, default: ImageSize = (640, 640)) -> ImageSize:
    """Return an Ultralytics image size as ``(height, width)``.

    A single legacy value remains square; rectangular text is entered as
    ``width x height`` so it follows the page label and common display order.
    """

    if isinstance(value, tuple) and len(value) == 2:
        height, width = value
    elif isinstance(value, list) and len(value) == 2:
        height, width = value
    elif isinstance(value, int) and not isinstance(value, bool):
        height = width = value
    else:
        text = str(value or "").strip().lower().replace("×", "x")
        if not text:
            return default
        parts = [part.strip() for part in text.replace(",", "x").split("x")]
        try:
            if len(parts) == 1:
                height = width = int(parts[0])
            elif len(parts) == 2:
                width, height = (int(part) for part in parts)
            else:
                return default
        except ValueError:
            return default
    return int(height), int(width)


def validate_image_size(value: ImageSizeValue) -> ImageSize:
    size = parse_image_size(value, default=(0, 0))
    height, width = size
    if height < 32 or width < 32 or height % 32 or width % 32:
        raise ValueError("输入尺寸的宽和高都必须是不小于 32 的 32 倍数。")
    return size


def format_image_size(value: ImageSizeValue) -> str:
    height, width = parse_image_size(value)
    return f"{width}×{height}"


__all__ = ["ImageSize", "ImageSizeValue", "format_image_size", "parse_image_size", "validate_image_size"]
