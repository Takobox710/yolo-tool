from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

_SPLITS = ("train", "val", "test")
_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp"}


def has_split_annotation_data(dataset_dir: Path) -> bool:
    for split in _SPLITS:
        for label_path in (dataset_dir / split / "labels").glob("*.txt"):
            if _has_nonempty_label_file(label_path):
                return True
    return False


def build_folder_distribution_data(images_dir: Path, annotations_dir: Path, labels_dir: Path, class_names: Sequence[str]) -> tuple[dict[str, Any], list[str]]:
    names = [str(name).strip() for name in class_names if str(name).strip()]
    class_counts: dict[str, int] = {name: 0 for name in names}
    total_images = 0
    annotated_images = 0
    for image_path in _iter_image_files(images_dir):
        total_images += 1
        annotation_counts = _read_folder_annotation_counts(
            annotations_dir / f"{image_path.stem}.json",
            labels_dir / f"{image_path.stem}.txt",
            names,
        )
        if not annotation_counts:
            continue
        annotated_images += 1
        for name, count in annotation_counts.items():
            class_counts[name] = class_counts.get(name, 0) + count
    return {"total_images": total_images, "annotated_images": annotated_images, "class_counts": class_counts}, names


def _iter_image_files(images_dir: Path):
    if not images_dir.exists():
        return []
    return (path for path in images_dir.iterdir() if path.is_file() and path.suffix.lower() in _IMAGE_SUFFIXES)


def _read_folder_annotation_counts(json_path: Path, yolo_path: Path, class_names: list[str]) -> dict[str, int]:
    if json_path.exists():
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        counts: dict[str, int] = {}
        shapes = payload.get("shapes")
        if not isinstance(shapes, list):
            return counts
        for shape in shapes:
            if not isinstance(shape, dict):
                continue
            name = str(shape.get("label") or "").strip() or "目标名称"
            if name not in class_names:
                class_names.append(name)
            counts[name] = counts.get(name, 0) + 1
        return counts
    if not yolo_path.exists():
        return {}
    try:
        id_counts = read_label_class_id_counts(yolo_path)
    except OSError:
        return {}
    return {
        class_names[class_id]: count
        for class_id, count in id_counts.items()
        if 0 <= class_id < len(class_names)
    }


def count_dataset_split_images(dataset_dir: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for split in _SPLITS:
        image_dir = dataset_dir / split / "images"
        label_dir = dataset_dir / split / "labels"
        count = count_image_files(image_dir)
        if not count:
            count = sum(1 for path in label_dir.glob("*.txt") if _has_nonempty_label_file(path))
        counts[split] = count
    return counts


def count_dataset_annotated_images(dataset_dir: Path) -> int:
    return sum(
        1
        for split in _SPLITS
        for path in (dataset_dir / split / "labels").glob("*.txt")
        if _has_nonempty_label_file(path)
    )


def _has_nonempty_label_file(path: Path) -> bool:
    try:
        return any(line.strip() for line in path.read_text(encoding="utf-8").splitlines())
    except OSError:
        return False


def count_image_files(images_dir: Path) -> int:
    if not images_dir.exists():
        return 0
    return sum(1 for path in images_dir.iterdir() if path.is_file() and path.suffix.lower() in _IMAGE_SUFFIXES)


def count_annotation_files(annotations_dir: Path, labels_dir: Path) -> int:
    json_count = count_labelme_annotation_files(annotations_dir)
    return json_count or count_yolo_annotation_files(labels_dir)


def count_labelme_annotation_files(annotations_dir: Path) -> int:
    if not annotations_dir.exists():
        return 0
    total = 0
    for path in annotations_dir.glob("*.json"):
        try:
            shapes = json.loads(path.read_text(encoding="utf-8")).get("shapes")
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(shapes, list):
            total += len(shapes)
    return total


def count_yolo_annotation_files(labels_dir: Path) -> int:
    if not labels_dir.exists():
        return 0
    total = 0
    for path in labels_dir.glob("*.txt"):
        try:
            total += sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
        except OSError:
            continue
    return total


def build_distribution_data(dataset_dir: Path, configured_class_names: Sequence[str]) -> tuple[dict[str, int], dict[str, int], list[str]]:
    class_names = resolve_dataset_class_names(dataset_dir, configured_class_names)
    image_counts = {split: {name: 0 for name in class_names} for split in _SPLITS}
    object_counts = {split: {name: 0 for name in class_names} for split in _SPLITS}
    for split in _SPLITS:
        for path in (dataset_dir / split / "labels").glob("*.txt"):
            for class_id in read_label_class_ids(path):
                if 0 <= class_id < len(class_names):
                    image_counts[split][class_names[class_id]] += 1
            for class_id, count in read_label_class_id_counts(path).items():
                if 0 <= class_id < len(class_names):
                    object_counts[split][class_names[class_id]] += count
    default_class = class_names[0] if class_names else "目标名称"
    single_counts = {split: image_counts[split].get(default_class, 0) for split in _SPLITS}
    multi_counts = {name: sum(object_counts[split].get(name, 0) for split in _SPLITS) for name in class_names}
    return single_counts, multi_counts, class_names


def resolve_dataset_class_names(dataset_dir: Path, configured_class_names: Sequence[str]) -> list[str]:
    yaml_path = dataset_dir / "data.yaml"
    if yaml_path.exists():
        for line in yaml_path.read_text(encoding="utf-8").splitlines():
            if not line.strip().startswith("names:"):
                continue
            raw_names = line.split(":", 1)[1].strip()
            try:
                parsed = json.loads(raw_names.replace("'", '"'))
            except json.JSONDecodeError:
                parsed = []
            names = [str(name).strip() for name in parsed if str(name).strip()]
            if names:
                return names
    names = [str(name).strip() for name in configured_class_names if str(name).strip()]
    return names or ["目标名称"]


def read_label_class_ids(label_path: Path) -> set[int]:
    return set(read_label_class_id_counts(label_path))


def read_label_class_id_counts(label_path: Path) -> dict[int, int]:
    counts: dict[int, int] = {}
    for line in label_path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if not parts:
            continue
        try:
            class_id = int(float(parts[0]))
        except ValueError:
            continue
        counts[class_id] = counts.get(class_id, 0) + 1
    return counts
