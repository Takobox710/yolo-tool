from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

from src.services.conversion.types import ConversionConfig, IMAGE_SUFFIXES


def image_files(folder: Path) -> list[Path]:
    if not Path(folder).exists():
        return []
    return sorted(
        path
        for path in Path(folder).iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )


def collect_inputs(config: ConversionConfig) -> tuple[list[tuple[Path, Path]], list[Path]]:
    labeled: list[tuple[Path, Path]] = []
    unlabeled: list[Path] = []
    suffix = ".json" if config.source_format == "labelme" else ".txt"
    label_map = {
        path.stem: path for path in Path(config.annotations_dir).glob(f"*{suffix}")
    }
    for image_path in image_files(config.images_dir):
        label_path = label_map.get(image_path.stem)
        if not label_path:
            unlabeled.append(image_path)
            continue
        if config.source_format == "labelme" and _labelme_has_no_shapes(label_path):
            unlabeled.append(image_path)
            continue
        labeled.append((image_path, label_path))
    return labeled, unlabeled


def split_labeled(
    items: list[tuple[Path, Path]], config: ConversionConfig
) -> dict[str, list[tuple[Path, Path]]]:
    rng = random.Random(config.random_seed)
    shuffled = items[:]
    rng.shuffle(shuffled)
    total = len(shuffled)
    train_count = int(round(total * config.train_ratio))
    val_count = int(round(total * config.val_ratio))
    if config.train_ratio == 1.0:
        train_count, val_count = total, 0
    test_count = max(0, total - train_count - val_count)
    if train_count + val_count + test_count > total:
        train_count = max(0, total - val_count - test_count)
    return {
        "train": shuffled[:train_count],
        "val": shuffled[train_count : train_count + val_count],
        "test": shuffled[train_count + val_count :],
    }


def add_label_stats(
    split_stats: defaultdict[str, int],
    lines: list[str],
    class_names: list[str],
    missing_labels: dict[str, list[str]],
    source_name: str,
) -> None:
    for line in lines:
        parts = line.split()
        if not parts:
            continue
        try:
            class_id = int(float(parts[0]))
        except ValueError:
            missing_labels["invalid-class-id"].append(source_name)
            continue
        if 0 <= class_id < len(class_names):
            split_stats[class_names[class_id]] += 1
        else:
            missing_labels[f"class-id:{class_id}"].append(source_name)


def build_empty_stats() -> dict[str, defaultdict[str, int]]:
    return {
        "train": defaultdict(int),
        "val": defaultdict(int),
        "test": defaultdict(int),
    }


def _labelme_has_no_shapes(label_path: Path) -> bool:
    try:
        payload = json.loads(label_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return True
    return not payload.get("shapes")
