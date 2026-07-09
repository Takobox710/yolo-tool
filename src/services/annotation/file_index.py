from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from src.services.data_ops import natural_sort_key


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp"}


def scan_annotation_image_items(image_dir: Path) -> list[Path]:
    if not image_dir.exists():
        return []
    return sorted(
        [
            path
            for path in image_dir.iterdir()
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
        ],
        key=natural_sort_key,
    )


def annotation_exists(json_path: Path, yolo_path: Path) -> bool:
    if json_path.exists():
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return False
        return bool(payload.get("shapes"))
    if yolo_path.exists():
        try:
            return any(
                line.strip() for line in yolo_path.read_text(encoding="utf-8").splitlines()
            )
        except OSError:
            return False
    return False


def collect_annotation_presence(
    image_paths: Iterable[Path],
    annotations_dir: Path,
    labels_dir: Path,
) -> dict[str, bool]:
    statuses: dict[str, bool] = {}
    for image_path in image_paths:
        json_path = annotations_dir / f"{image_path.stem}.json"
        yolo_path = labels_dir / f"{image_path.stem}.txt"
        statuses[_status_key(image_path)] = annotation_exists(json_path, yolo_path)
    return statuses


def _status_key(path: Path) -> str:
    return str(Path(path).resolve())
