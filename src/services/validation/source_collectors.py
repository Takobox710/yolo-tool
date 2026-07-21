from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.services.validation.model_catalog import (
    IMAGE_SUFFIXES,
    SOURCE_SUFFIXES,
    VIDEO_SUFFIXES,
    natural_sort_key,
)


def collect_dataset_prediction_sources(
    dataset_yaml: str | Path,
    source_scope: str = "全部图片",
) -> list[Path]:
    yaml_path = Path(dataset_yaml)
    if not yaml_path.exists() or yaml_path.suffix.lower() not in {".yaml", ".yml"}:
        return []
    try:
        payload = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(payload, dict):
        return []

    dataset_root_value = payload.get("path")
    if dataset_root_value:
        dataset_root = _resolve_dataset_entry_path(
            dataset_root_value, yaml_path, yaml_path.parent
        )
    else:
        dataset_root = yaml_path.parent.resolve()

    scope_map = {
        "训练图片": ["train"],
        "验证图片": ["val"],
        "测试图片": ["test"],
        "全部图片": ["train", "val", "test"],
    }
    selected_splits = scope_map.get(
        str(source_scope).strip(), ["train", "val", "test"]
    )
    results: list[Path] = []
    seen: set[str] = set()
    for split in selected_splits:
        for path in _collect_media_from_dataset_entry(
            payload.get(split), yaml_path, dataset_root
        ):
            resolved = str(path.resolve())
            if resolved in seen:
                continue
            seen.add(resolved)
            results.append(path.resolve())
    return results


def collect_prediction_sources(
    source_mode: str,
    source_path: str | Path,
    *,
    dataset_yaml: str | Path | None = None,
    source_scope: str = "全部图片",
) -> list[Path]:
    source_text = str(source_path or "").strip()
    source = Path(source_text) if source_text else None
    if source_mode in {
        "图片检测",
        "视频检测",
        "图片文件夹",
        "视频文件夹",
        "图片/视频文件夹",
    }:
        if source_mode in {"图片检测", "图片文件夹"}:
            suffixes = IMAGE_SUFFIXES
        elif source_mode in {"视频检测", "视频文件夹"}:
            suffixes = VIDEO_SUFFIXES
        else:
            suffixes = SOURCE_SUFFIXES
        if source is not None and source.is_file():
            return [source.resolve()] if source.suffix.lower() in suffixes else []
        if source is not None and source.exists() and source.is_dir():
            return sorted(
                (
                    path
                    for path in source.iterdir()
                    if path.is_file() and path.suffix.lower() in suffixes
                ),
                key=natural_sort_key,
            )
        if dataset_yaml:
            return collect_dataset_prediction_sources(dataset_yaml, source_scope)
        return []
    if source_mode == "图片/视频" and source is not None:
        return (
            [source]
            if source.is_file() and source.suffix.lower() in SOURCE_SUFFIXES
            else []
        )
    return []


def dataset_sort_key(path: Path) -> tuple[str, list[object]]:
    return (str(path.parent).lower(), natural_sort_key(path))


def _resolve_dataset_entry_path(
    raw_path: str | Path,
    yaml_path: Path,
    dataset_root: Path,
) -> Path:
    path = Path(str(raw_path))
    if path.is_absolute():
        return path
    candidate = dataset_root / path
    if candidate.exists():
        return candidate
    return (yaml_path.parent / path).resolve()


def _collect_media_from_dataset_entry(
    entry: Any,
    yaml_path: Path,
    dataset_root: Path,
) -> list[Path]:
    if isinstance(entry, list):
        items: list[Path] = []
        for value in entry:
            items.extend(_collect_media_from_dataset_entry(value, yaml_path, dataset_root))
        return items
    if not isinstance(entry, str) or not entry.strip():
        return []
    target = _resolve_dataset_entry_path(entry.strip(), yaml_path, dataset_root)
    if not target.exists():
        return []
    if target.is_dir():
        return sorted(
            (
                path
                for path in target.rglob("*")
                if path.is_file() and path.suffix.lower() in SOURCE_SUFFIXES
            ),
            key=dataset_sort_key,
        )
    if target.suffix.lower() == ".txt":
        lines = target.read_text(encoding="utf-8").splitlines()
        items: list[Path] = []
        for line in lines:
            resolved = _resolve_dataset_entry_path(line.strip(), target, dataset_root)
            if resolved.is_file() and resolved.suffix.lower() in SOURCE_SUFFIXES:
                items.append(resolved)
        return sorted(items, key=dataset_sort_key)
    if target.is_file() and target.suffix.lower() in SOURCE_SUFFIXES:
        return [target]
    return []
