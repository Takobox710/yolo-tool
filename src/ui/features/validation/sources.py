from __future__ import annotations

from pathlib import Path
from typing import Callable

from src.services.validation import collect_prediction_sources

SOURCE_SCOPE_OPTIONS = ["全部图片", "训练图片", "验证图片", "测试图片"]


def dataset_split_image_dir(dataset_dir: Path, split: str) -> Path:
    return (dataset_dir / split / "images").resolve()


def scope_target_path(scope: str, paths_settings: dict) -> Path:
    scope = str(scope or "全部图片").strip()
    dataset_dir = Path(paths_settings["dataset_dir"])
    if scope == "全部图片":
        return Path(paths_settings["images_dir"]).resolve()
    if scope == "训练图片":
        return dataset_split_image_dir(dataset_dir, "train")
    if scope == "验证图片":
        return dataset_split_image_dir(dataset_dir, "val")
    if scope == "测试图片":
        return dataset_split_image_dir(dataset_dir, "test")
    return Path(paths_settings["images_dir"]).resolve()


def folder_source_path_for_selection(
    text: str,
    paths_settings: dict,
    resolve_text: Callable[[str], str],
) -> str:
    source_text = str(text or "").strip()
    if source_text in SOURCE_SCOPE_OPTIONS:
        return str(scope_target_path(source_text, paths_settings))
    return resolve_text(source_text)


def collect_validation_source_items(
    *,
    mode: str,
    is_val_mode: bool,
    source_text: str,
    paths_settings: dict,
    resolve_text: Callable[[str], str],
) -> list[Path]:
    if mode == "摄像头" or is_val_mode:
        return []
    source_path = folder_source_path_for_selection(
        source_text,
        paths_settings,
        resolve_text,
    )
    if mode == "图片/视频":
        source_path = resolve_text(source_text)
    return collect_prediction_sources(mode, source_path)

