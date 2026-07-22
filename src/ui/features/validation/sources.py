from __future__ import annotations

from pathlib import Path
from typing import Callable

from src.services.validation import collect_prediction_sources, is_live_source_mode

SOURCE_SCOPE_OPTIONS = ["全部图片", "训练图片", "验证图片", "测试图片"]
IMAGE_SOURCE_OPTIONS = [*SOURCE_SCOPE_OPTIONS, "单张图片"]
VIDEO_SOURCE_OPTIONS = ["批量视频", "单个视频"]
SINGLE_FILE_SOURCE_OPTIONS = {"单张图片", "单个视频"}
CUSTOM_SOURCE_OPTIONS = {"单张图片", "批量视频", "单个视频"}


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
    selected_source_path: str | Path = "",
) -> str:
    source_text = str(text or "").strip()
    if source_text in SOURCE_SCOPE_OPTIONS:
        return str(scope_target_path(source_text, paths_settings))
    if source_text in CUSTOM_SOURCE_OPTIONS:
        return str(selected_source_path or "")
    return resolve_text(source_text)


def collect_validation_source_items(
    *,
    mode: str,
    is_val_mode: bool,
    source_text: str,
    paths_settings: dict,
    resolve_text: Callable[[str], str],
    selected_source_path: str | Path = "",
) -> list[Path]:
    if is_live_source_mode(mode) or is_val_mode:
        return []
    source_path = folder_source_path_for_selection(
        source_text,
        paths_settings,
        resolve_text,
        selected_source_path,
    )
    return collect_prediction_sources(mode, source_path)

