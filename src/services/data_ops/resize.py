from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from src.services.data_ops.rename import natural_sort_key


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp"}
RESIZE_MODE_CANVAS = "画布压缩"
RESIZE_MODE_CROP = "裁剪"
ASPECT_RATIOS = {
    "1:1": (1, 1),
    "4:3": (4, 3),
    "16:9": (16, 9),
    "3:4": (3, 4),
    "9:16": (9, 16),
}


@dataclass
class ResizeConfig:
    source_dir: Path
    output_dir: Path
    backup_dir: Path
    long_edge: int = 960
    canvas_size: int = 960
    background: str = "white"
    backup_enabled: bool = False
    mode: str = RESIZE_MODE_CANVAS
    aspect_ratio: str = "1:1"
    resolution: str | None = None


@dataclass
class ResizePlanItem:
    source: Path
    output: Path
    original_size: tuple[int, int]
    resized_size: tuple[int, int]
    scale: float
    output_size: tuple[int, int]
    crop_box: tuple[int, int, int, int] | None = None


@dataclass
class ResizePreview:
    items: list[ResizePlanItem]
    backup_dir: Path


@dataclass
class ResizeResult:
    processed_count: int
    backup_dir: Path
    output_dir: Path


def _image_files(folder: Path) -> list[Path]:
    if not Path(folder).exists():
        return []
    return sorted(
        (
            path
            for path in Path(folder).rglob("*")
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
        ),
        key=natural_sort_key,
    )


def parse_resolution(value: str | tuple[int, int] | None, fallback: int) -> tuple[int, int]:
    if isinstance(value, tuple) and len(value) == 2:
        width, height = value
    else:
        text = str(value or "").strip().lower().replace("×", "x")
        parts = [part.strip() for part in text.split("x")]
        if len(parts) == 1 and parts[0].isdigit():
            width = height = int(parts[0])
        elif len(parts) == 2 and all(part.isdigit() for part in parts):
            width, height = (int(part) for part in parts)
        elif not text:
            width = height = fallback
        else:
            raise ValueError("分辨率必须使用“宽×高”格式，例如 640×480。")
    if width <= 0 or height <= 0:
        raise ValueError("分辨率的宽和高必须大于 0。")
    return int(width), int(height)


def _target_size(config: ResizeConfig) -> tuple[int, int]:
    width, height = parse_resolution(config.resolution, config.canvas_size)
    ratio = ASPECT_RATIOS.get(config.aspect_ratio)
    if ratio is None:
        raise ValueError(f"不支持的图片比例：{config.aspect_ratio}")
    if width * ratio[1] != height * ratio[0]:
        raise ValueError(
            f"分辨率 {width}×{height} 与所选比例 {config.aspect_ratio} 不一致。"
        )
    return width, height


def _center_crop_box(
    original_size: tuple[int, int], target_size: tuple[int, int]
) -> tuple[int, int, int, int]:
    width, height = original_size
    target_width, target_height = target_size
    if width * target_height > height * target_width:
        crop_width = round(height * target_width / target_height)
        left = (width - crop_width) // 2
        return left, 0, left + crop_width, height
    crop_height = round(width * target_height / target_width)
    top = (height - crop_height) // 2
    return 0, top, width, top + crop_height


def preview_resize(config: ResizeConfig) -> ResizePreview:
    target_size = _target_size(config)
    if config.mode not in {RESIZE_MODE_CANVAS, RESIZE_MODE_CROP}:
        raise ValueError(f"不支持的处理模式：{config.mode}")
    items: list[ResizePlanItem] = []
    for source in _image_files(config.source_dir):
        with Image.open(source) as image:
            width, height = image.size
        if config.mode == RESIZE_MODE_CANVAS:
            scale = min(target_size[0] / width, target_size[1] / height)
            resized_size = (max(1, round(width * scale)), max(1, round(height * scale)))
            crop_box = None
        else:
            crop_box = _center_crop_box((width, height), target_size)
            crop_width = crop_box[2] - crop_box[0]
            crop_height = crop_box[3] - crop_box[1]
            scale = target_size[0] / crop_width
            resized_size = target_size
        relative_source = source.relative_to(config.source_dir)
        items.append(
            ResizePlanItem(
                source=source,
                output=Path(config.output_dir) / relative_source,
                original_size=(width, height),
                resized_size=resized_size,
                scale=scale,
                output_size=target_size,
                crop_box=crop_box,
            )
        )
    return ResizePreview(items=items, backup_dir=Path(config.backup_dir))


def run_resize(config: ResizeConfig) -> ResizeResult:
    preview = preview_resize(config)
    Path(config.output_dir).mkdir(parents=True, exist_ok=True)
    if config.backup_enabled:
        Path(config.backup_dir).mkdir(parents=True, exist_ok=True)
    background = (255, 255, 255) if config.background == "white" else (0, 0, 0)
    for item in preview.items:
        if config.backup_enabled:
            backup_target = Path(config.backup_dir) / item.source.relative_to(
                config.source_dir
            )
            backup_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item.source, backup_target)
        with Image.open(item.source).convert("RGB") as image:
            if config.mode == RESIZE_MODE_CROP:
                assert item.crop_box is not None
                output = image.crop(item.crop_box).resize(
                    item.output_size, Image.Resampling.LANCZOS
                )
            else:
                resized = image.resize(item.resized_size, Image.Resampling.LANCZOS)
                output = Image.new("RGB", item.output_size, background)
                x = (item.output_size[0] - item.resized_size[0]) // 2
                y = (item.output_size[1] - item.resized_size[1]) // 2
                output.paste(resized, (x, y))
            item.output.parent.mkdir(parents=True, exist_ok=True)
            output.save(item.output)
    return ResizeResult(processed_count=len(preview.items), backup_dir=Path(config.backup_dir), output_dir=Path(config.output_dir))

