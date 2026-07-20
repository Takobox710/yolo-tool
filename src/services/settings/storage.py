from __future__ import annotations

import os
from copy import deepcopy
from pathlib import Path
from typing import Any


PROJECT_PATH_FIELDS: dict[tuple[str, ...], dict[str, bool]] = {
    ("project", "root"): {},
    ("paths", "images_dir"): {},
    ("paths", "annotations_dir"): {},
    ("paths", "labels_dir"): {},
    ("paths", "dataset_dir"): {},
    ("paths", "models_dir"): {},
    ("paths", "result_dir"): {},
    ("image_resize", "source_dir"): {},
    ("image_resize", "output_dir"): {},
    ("image_resize", "backup_dir"): {},
    ("training", "data"): {},
    ("training", "model_yaml"): {},
    ("training", "project"): {},
    ("training", "pretrained"): {"keep_bare_name": True},
    ("validation", "model_path"): {"keep_bare_name": True},
    ("validation", "source_path"): {},
    ("validation", "save_dir"): {},
}


def deep_merge(defaults: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(defaults)
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def serialize_settings_for_storage(
    data: dict[str, Any], project_root: Path
) -> dict[str, Any]:
    serialized = deepcopy(data)
    resolved_root = Path(project_root).resolve()
    for keys, options in PROJECT_PATH_FIELDS.items():
        current = _get_nested(serialized, keys)
        if current is None:
            continue
        _set_nested(
            serialized,
            keys,
            _serialize_project_path(
                current,
                resolved_root,
                keep_bare_name=options.get("keep_bare_name", False),
            ),
        )
    return serialized


def deserialize_settings_from_storage(
    data: dict[str, Any], project_root: Path
) -> dict[str, Any]:
    deserialized = deepcopy(data)
    resolved_root = Path(project_root).resolve()
    for keys, options in PROJECT_PATH_FIELDS.items():
        current = _get_nested(deserialized, keys)
        if current is None:
            continue
        _set_nested(
            deserialized,
            keys,
            _deserialize_project_path(
                current,
                resolved_root,
                keep_bare_name=options.get("keep_bare_name", False),
            ),
        )
    return deserialized


def _get_nested(data: dict[str, Any], keys: tuple[str, ...]) -> Any:
    target: Any = data
    for key in keys:
        if not isinstance(target, dict) or key not in target:
            return None
        target = target[key]
    return target


def _set_nested(data: dict[str, Any], keys: tuple[str, ...], value: Any) -> None:
    target: dict[str, Any] = data
    for key in keys[:-1]:
        existing = target.get(key)
        if not isinstance(existing, dict):
            existing = {}
            target[key] = existing
        target = existing
    target[keys[-1]] = value


def _serialize_project_path(
    value: Any, project_root: Path, *, keep_bare_name: bool = False
) -> Any:
    text = str(value or "").strip()
    if not text:
        return value
    if _should_keep_bare_name(text, keep_bare_name):
        return text
    path = Path(os.path.expandvars(text)).expanduser()
    if not path.is_absolute():
        return str(path)
    resolved = path.resolve()
    if _is_under_root(resolved, project_root):
        relative = os.path.relpath(str(resolved), str(project_root))
        return "." if relative == "." else str(Path(relative))
    return str(resolved)


def _deserialize_project_path(
    value: Any, project_root: Path, *, keep_bare_name: bool = False
) -> Any:
    text = str(value or "").strip()
    if not text:
        return value
    if _should_keep_bare_name(text, keep_bare_name):
        return text
    path = Path(os.path.expandvars(text)).expanduser()
    if path.is_absolute():
        return str(path.resolve())
    return str((project_root / path).resolve())


def _is_under_root(path: Path, root: Path) -> bool:
    try:
        common = os.path.commonpath([str(path), str(root)])
    except ValueError:
        return False
    return os.path.normcase(common) == os.path.normcase(str(root))


def _should_keep_bare_name(text: str, keep_bare_name: bool) -> bool:
    if not keep_bare_name:
        return False
    path = Path(text)
    return len(path.parts) == 1 and text not in {".", ".."}
