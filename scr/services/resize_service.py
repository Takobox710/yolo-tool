from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from scr.services.rename_service import natural_sort_key


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp"}


@dataclass
class ResizeConfig:
    source_dir: Path
    output_dir: Path
    backup_dir: Path
    long_edge: int = 960
    canvas_size: int = 960
    background: str = "white"
    backup_enabled: bool = False


@dataclass
class ResizePlanItem:
    source: Path
    output: Path
    original_size: tuple[int, int]
    resized_size: tuple[int, int]
    scale: float


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


def preview_resize(config: ResizeConfig) -> ResizePreview:
    items: list[ResizePlanItem] = []
    for source in _image_files(config.source_dir):
        with Image.open(source) as image:
            width, height = image.size
        scale = config.canvas_size / max(width, height)
        resized_size = (max(1, round(width * scale)), max(1, round(height * scale)))
        relative_source = source.relative_to(config.source_dir)
        items.append(
            ResizePlanItem(
                source=source,
                output=Path(config.output_dir) / relative_source,
                original_size=(width, height),
                resized_size=resized_size,
                scale=scale,
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
            resized = image.resize(item.resized_size, Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", (config.canvas_size, config.canvas_size), background)
            x = (config.canvas_size - item.resized_size[0]) // 2
            y = (config.canvas_size - item.resized_size[1]) // 2
            canvas.paste(resized, (x, y))
            item.output.parent.mkdir(parents=True, exist_ok=True)
            canvas.save(item.output)
    return ResizeResult(processed_count=len(preview.items), backup_dir=Path(config.backup_dir), output_dir=Path(config.output_dir))
