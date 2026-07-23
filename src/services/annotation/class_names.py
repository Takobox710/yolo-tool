from __future__ import annotations

import json
from pathlib import Path


def collect_labelme_class_names(
    annotations_dir: Path, class_names: list[str] | None = None
) -> list[str]:
    """Return configured class names plus all non-empty Labelme labels in a project."""
    names = [str(name).strip() for name in (class_names or []) if str(name).strip()]
    known = set(names)
    root = Path(annotations_dir)
    if not root.exists():
        return names
    for json_path in sorted(root.rglob("*.json")):
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(payload, dict):
            continue
        for shape in payload.get("shapes", []):
            if not isinstance(shape, dict):
                continue
            label = str(shape.get("label") or "").strip()
            if label and label not in known:
                known.add(label)
                names.append(label)
    return names


def collect_labelme_class_counts(
    annotations_dir: Path, class_names: list[str]
) -> list[int]:
    counts = [0] * len(class_names)
    indexes = {name: index for index, name in enumerate(class_names)}
    root = Path(annotations_dir)
    if not root.exists():
        return counts
    for json_path in sorted(root.rglob("*.json")):
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(payload, dict):
            continue
        for shape in payload.get("shapes", []):
            if not isinstance(shape, dict):
                continue
            class_id = indexes.get(str(shape.get("label") or "").strip())
            if class_id is not None:
                counts[class_id] += 1
    return counts


def convert_labelme_classes(
    annotations_dir: Path, source_name: str, target_name: str
) -> int:
    converted = 0
    root = Path(annotations_dir)
    if not root.exists() or source_name == target_name:
        return converted
    for json_path in sorted(root.rglob("*.json")):
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(payload, dict):
            continue
        changed = False
        for shape in payload.get("shapes", []):
            if not isinstance(shape, dict) or shape.get("label") != source_name:
                continue
            shape["label"] = target_name
            converted += 1
            changed = True
        if changed:
            json_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
    return converted


__all__ = [
    "collect_labelme_class_counts",
    "collect_labelme_class_names",
    "convert_labelme_classes",
]
