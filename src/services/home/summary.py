from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.services.training import read_results_csv_for_curves, read_train_metrics
from src.services.validation import scan_candidate_models


def build_home_summary(
    *,
    images_dir: Path,
    annotations_dir: Path,
    labels_dir: Path,
    dataset_dir: Path,
    result_dir: Path,
    configured_class_names: Sequence[str],
) -> dict[str, Any]:
    single_counts, multi_counts, class_names = build_distribution_data(
        dataset_dir, configured_class_names
    )
    return {
        "image_count": count_image_files(images_dir),
        "label_count": count_annotation_files(annotations_dir, labels_dir),
        "single_counts": single_counts,
        "multi_counts": multi_counts,
        "class_names": class_names,
        "curve_data": read_results_csv_for_curves(result_dir),
        "history_entries": collect_home_history_entries(result_dir),
    }


def count_image_files(images_dir: Path) -> int:
    if not images_dir.exists():
        return 0
    total = 0
    for path in images_dir.iterdir():
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}:
            total += 1
    return total


def count_annotation_files(annotations_dir: Path, labels_dir: Path) -> int:
    json_count = count_labelme_annotation_files(annotations_dir)
    if json_count:
        return json_count
    return count_yolo_annotation_files(labels_dir)


def count_labelme_annotation_files(annotations_dir: Path) -> int:
    if not annotations_dir.exists():
        return 0
    total = 0
    for label_path in annotations_dir.glob("*.json"):
        try:
            payload = json.loads(label_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if payload.get("shapes"):
            total += 1
    return total


def count_yolo_annotation_files(labels_dir: Path) -> int:
    if not labels_dir.exists():
        return 0
    total = 0
    for label_path in labels_dir.glob("*.txt"):
        try:
            has_label = any(
                line.strip()
                for line in label_path.read_text(encoding="utf-8").splitlines()
            )
        except OSError:
            continue
        if has_label:
            total += 1
    return total


def build_distribution_data(
    dataset_dir: Path,
    configured_class_names: Sequence[str],
) -> tuple[dict[str, int], dict[str, int], list[str]]:
    class_names = resolve_dataset_class_names(dataset_dir, configured_class_names)
    split_class_counts: dict[str, dict[str, int]] = {
        split: {name: 0 for name in class_names} for split in ("train", "val", "test")
    }
    for split in ("train", "val", "test"):
        label_dir = dataset_dir / split / "labels"
        if not label_dir.exists():
            continue
        for label_path in label_dir.glob("*.txt"):
            present_ids = read_label_class_ids(label_path)
            for class_id in present_ids:
                if 0 <= class_id < len(class_names):
                    split_class_counts[split][class_names[class_id]] += 1
    default_class = class_names[0] if class_names else "数据集"
    single_counts = {
        split: split_class_counts[split].get(default_class, 0)
        for split in ("train", "val", "test")
    }
    multi_counts = {
        name: sum(
            split_class_counts[split].get(name, 0)
            for split in ("train", "val", "test")
        )
        for name in class_names
    }
    return single_counts, multi_counts, class_names


def resolve_dataset_class_names(
    dataset_dir: Path, configured_class_names: Sequence[str]
) -> list[str]:
    yaml_path = dataset_dir / "data.yaml"
    if yaml_path.exists():
        text = yaml_path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.strip().startswith("names:"):
                _, raw_names = line.split(":", 1)
                raw_names = raw_names.strip()
                try:
                    parsed = json.loads(raw_names.replace("'", '"'))
                except json.JSONDecodeError:
                    parsed = []
                names = [str(name).strip() for name in parsed if str(name).strip()]
                if names:
                    return names
    names = [str(name).strip() for name in configured_class_names if str(name).strip()]
    return names or ["weld"]


def read_label_class_ids(label_path: Path) -> set[int]:
    present_ids: set[int] = set()
    for line in label_path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if not parts:
            continue
        try:
            present_ids.add(int(float(parts[0])))
        except ValueError:
            continue
    return present_ids


def collect_home_history_entries(
    result_dir: Path, *, limit: int = 8
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for candidate in scan_candidate_models(result_dir)[:limit]:
        run_dir = candidate.parent.parent
        model_name = candidate.name
        entries.append(
            {
                "train_id": run_dir.name,
                "model_name": model_name,
                "metrics": read_train_metrics(run_dir, model_name),
            }
        )
    return entries
