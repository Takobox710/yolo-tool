from __future__ import annotations

import json
import math
import random
import shutil
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp"}


@dataclass
class ConversionConfig:
    task_mode: str
    images_dir: Path
    annotations_dir: Path
    output_dir: Path
    labels_dir: Path
    class_names: list[str] | None = None
    source_format: str = "labelme"
    train_ratio: float = 0.7
    val_ratio: float = 0.2
    test_ratio: float = 0.1
    random_seed: int = 42
    line_to_obb: bool = True
    line_half_width: float = 10.0
    backup_existing: bool = True

    def validate(self) -> "ConversionConfig":
        if self.task_mode not in {"obb", "detect"}:
            raise ValueError("task_mode 必须是 obb 或 detect")
        if self.source_format not in {"labelme", "yolo"}:
            raise ValueError("source_format 必须是 labelme 或 yolo")
        ratio_sum = self.train_ratio + self.val_ratio + self.test_ratio
        if round(ratio_sum, 6) != 1.0:
            raise ValueError(f"数据集划分比例之和必须为 1.0，当前为 {ratio_sum:.6f}")
        if self.line_half_width <= 0:
            raise ValueError("线宽半径必须大于 0")
        return self


@dataclass
class ConversionPreview:
    labeled_count: int
    unlabeled_count: int
    output_dir: Path
    labels_dir: Path
    planned_splits: dict[str, int]


@dataclass
class ConversionResult:
    labeled_train_count: int
    labeled_val_count: int
    labeled_test_count: int
    total_boxes: int
    unlabeled_count: int
    yaml_path: Path
    labels_dir: Path
    missing_labels: dict[str, list[str]]
    stats: dict[str, dict[str, int]]
    class_names: list[str]


def image_files(folder: Path) -> list[Path]:
    if not Path(folder).exists():
        return []
    return sorted(path for path in Path(folder).iterdir() if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES)


def collect_inputs(config: ConversionConfig) -> tuple[list[tuple[Path, Path]], list[Path]]:
    labeled: list[tuple[Path, Path]] = []
    unlabeled: list[Path] = []
    suffix = ".json" if config.source_format == "labelme" else ".txt"
    label_map = {path.stem: path for path in Path(config.annotations_dir).glob(f"*{suffix}")}
    for image_path in image_files(config.images_dir):
        label_path = label_map.get(image_path.stem)
        if not label_path:
            unlabeled.append(image_path)
            continue
        if config.source_format == "labelme":
            try:
                payload = json.loads(label_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                unlabeled.append(image_path)
                continue
            if not payload.get("shapes"):
                unlabeled.append(image_path)
                continue
        labeled.append((image_path, label_path))
    return labeled, unlabeled


def split_labeled(items: list[tuple[Path, Path]], config: ConversionConfig) -> dict[str, list[tuple[Path, Path]]]:
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


def preview_conversion(config: ConversionConfig) -> ConversionPreview:
    active = config.validate()
    labeled, unlabeled = collect_inputs(active)
    split_map = split_labeled(labeled, active)
    return ConversionPreview(
        labeled_count=len(labeled),
        unlabeled_count=len(unlabeled),
        output_dir=active.output_dir,
        labels_dir=active.labels_dir,
        planned_splits={key: len(value) for key, value in split_map.items()},
    )


def run_conversion(config: ConversionConfig) -> ConversionResult:
    active = config.validate()
    labeled, unlabeled = collect_inputs(active)
    if not labeled:
        raise ValueError("没有找到可转换的已标注图片")
    class_names = detect_class_names(active, labeled)
    active.class_names = class_names

    split_map = split_labeled(labeled, active)
    _prepare_output_dirs(active)

    stats: dict[str, defaultdict[str, int]] = {
        "train": defaultdict(int),
        "val": defaultdict(int),
        "test": defaultdict(int),
    }
    missing_labels: defaultdict[str, list[str]] = defaultdict(list)
    total_boxes = 0
    for split, pairs in split_map.items():
        split_dir = active.output_dir / split
        for image_path, label_source_path in pairs:
            shutil.copy2(image_path, split_dir / "images" / image_path.name)
            if active.source_format == "labelme":
                lines = convert_label_file(label_source_path, active, missing_labels)
                label_text = "\n".join(lines) + ("\n" if lines else "")
            else:
                label_text = label_source_path.read_text(encoding="utf-8")
                lines = [line.strip() for line in label_text.splitlines() if line.strip()]
            target_label_path = split_dir / "labels" / f"{image_path.stem}.txt"
            target_label_path.write_text(label_text, encoding="utf-8")
            shutil.copy2(target_label_path, active.labels_dir / target_label_path.name)
            _add_label_stats(stats[split], lines, active.class_names, missing_labels, label_source_path.name)
            total_boxes += len(lines)

    yaml_path = write_data_yaml(active)
    return ConversionResult(
        labeled_train_count=len(split_map["train"]),
        labeled_val_count=len(split_map["val"]),
        labeled_test_count=len(split_map["test"]),
        total_boxes=total_boxes,
        unlabeled_count=len(unlabeled),
        yaml_path=yaml_path,
        labels_dir=active.labels_dir,
        missing_labels={key: value[:] for key, value in missing_labels.items()},
        stats={key: dict(value) for key, value in stats.items()},
        class_names=class_names,
    )


def detect_class_names(config: ConversionConfig, labeled: list[tuple[Path, Path]] | None = None) -> list[str]:
    existing = [str(name).strip() for name in (config.class_names or []) if str(name).strip()]
    if existing:
        return existing
    pairs = labeled if labeled is not None else collect_inputs(config)[0]
    if config.source_format == "labelme":
        names: list[str] = []
        seen: set[str] = set()
        for _image_path, label_path in pairs:
            try:
                payload = json.loads(label_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            for shape in payload.get("shapes", []):
                label = str(shape.get("label") or "").strip()
                if label and label not in seen:
                    seen.add(label)
                    names.append(label)
        if names:
            return names
    max_class_id = -1
    for _image_path, label_path in pairs:
        for line in label_path.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if not parts:
                continue
            try:
                max_class_id = max(max_class_id, int(float(parts[0])))
            except ValueError:
                continue
    if max_class_id >= 0:
        return [f"class_{index}" for index in range(max_class_id + 1)]
    raise ValueError("未能自动识别类别，请检查标注文件是否包含有效类别")


def _add_label_stats(
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


def _prepare_output_dirs(config: ConversionConfig) -> None:
    if config.output_dir.exists():
        if config.backup_existing:
            backup = config.output_dir / "old"
            backup.mkdir(parents=True, exist_ok=True)
        for split in ("train", "val", "test"):
            split_path = config.output_dir / split
            if split_path.exists():
                shutil.rmtree(split_path)
    for split in ("train", "val", "test"):
        (config.output_dir / split / "images").mkdir(parents=True, exist_ok=True)
        (config.output_dir / split / "labels").mkdir(parents=True, exist_ok=True)
    if config.labels_dir.exists():
        shutil.rmtree(config.labels_dir)
    config.labels_dir.mkdir(parents=True, exist_ok=True)


def convert_label_file(json_path: Path, config: ConversionConfig, missing_labels: dict[str, list[str]]) -> list[str]:
    payload = json.loads(Path(json_path).read_text(encoding="utf-8"))
    width = payload.get("imageWidth")
    height = payload.get("imageHeight")
    if not width or not height:
        raise ValueError(f"{json_path.name} 缺少 imageWidth/imageHeight")

    lines: list[str] = []
    for shape in payload.get("shapes", []):
        label = shape.get("label")
        if label not in config.class_names:
            missing_labels[label or "unknown"].append(Path(json_path).name)
            continue
        class_id = config.class_names.index(label)
        if config.task_mode == "obb":
            points = shape_to_obb_points(shape, config)
            if points is None:
                missing_labels[f"{label}(unsupported)"].append(Path(json_path).name)
                continue
            coords = normalize_points(points, width, height)
            lines.append(f"{class_id} " + " ".join(f"{value:.6f}" for pair in coords for value in pair))
        else:
            bbox = shape_to_detect_bbox(shape)
            if bbox is None:
                missing_labels[f"{label}(unsupported)"].append(Path(json_path).name)
                continue
            x_center, y_center, box_width, box_height = bbox
            lines.append(
                f"{class_id} {x_center / width:.6f} {y_center / height:.6f} {box_width / width:.6f} {box_height / height:.6f}"
            )
    return lines


def shape_to_obb_points(shape: dict, config: ConversionConfig) -> list[tuple[float, float]] | None:
    points = shape.get("points", [])
    shape_type = shape.get("shape_type", "")
    if shape_type == "oriented_rectangle" and len(points) == 4:
        return [(float(x), float(y)) for x, y in points]
    if shape_type == "rectangle" and len(points) == 2:
        (x1, y1), (x2, y2) = points
        return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
    if shape_type == "line" and len(points) == 2 and config.line_to_obb:
        (x1, y1), (x2, y2) = points
        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy)
        if length == 0:
            return None
        nx = -dy / length
        ny = dx / length
        half = config.line_half_width
        return [
            (x1 + nx * half, y1 + ny * half),
            (x2 + nx * half, y2 + ny * half),
            (x2 - nx * half, y2 - ny * half),
            (x1 - nx * half, y1 - ny * half),
        ]
    return None


def shape_to_detect_bbox(shape: dict) -> tuple[float, float, float, float] | None:
    points = shape.get("points", [])
    if len(points) < 2:
        return None
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    x1, x2 = min(xs), max(xs)
    y1, y2 = min(ys), max(ys)
    return ((x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1)


def normalize_points(points: Iterable[tuple[float, float]], width: float, height: float) -> list[tuple[float, float]]:
    normalized = []
    for x, y in points:
        normalized.append((max(0.0, min(1.0, x / width)), max(0.0, min(1.0, y / height))))
    return normalized


def write_data_yaml(config: ConversionConfig) -> Path:
    yaml_path = config.output_dir / "data.yaml"
    yaml_path.write_text(
        "\n".join(
            [
                f"path: {config.output_dir.parent.as_posix()}",
                f"train: {config.output_dir.name}/train/images",
                f"val: {config.output_dir.name}/val/images",
                f"test: {config.output_dir.name}/test/images",
                f"nc: {len(config.class_names)}",
                f"names: {config.class_names}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return yaml_path


def format_conversion_result(result: ConversionResult, config: ConversionConfig, preview: bool = False) -> str:
    total_images = result.labeled_train_count + result.labeled_val_count + result.labeled_test_count
    title = "转换预览" if preview else "转换完成"
    operation = "Labelme 转 YOLO 并分组" if config.source_format == "labelme" else "YOLO 标注分组"
    lines = [
        f"{title}！",
        "",
        f"模式: {operation}",
        f"任务类型: {config.task_mode}",
        "",
        "数据集划分:",
        _format_split_line("训练集", "train", result.labeled_train_count, result.stats),
        _format_split_line("验证集", "val", result.labeled_val_count, result.stats),
        _format_split_line("测试集", "test", result.labeled_test_count, result.stats),
        "",
        "总体统计:",
        f"  - 有标注图片: {total_images} 张",
        f"  - 无标注图片: {result.unlabeled_count} 张",
        f"  - 标注总数: {result.total_boxes}",
        "",
        "类别统计:",
    ]
    class_names = getattr(result, "class_names", None) or config.class_names or []
    for class_name in class_names:
        train = result.stats.get("train", {}).get(class_name, 0)
        val = result.stats.get("val", {}).get(class_name, 0)
        test = result.stats.get("test", {}).get(class_name, 0)
        lines.append(f"  - {class_name}: train={train}, val={val}, test={test}, total={train + val + test}")
    if result.missing_labels:
        lines.extend(["", "跳过或未知标签:"])
        for label, names in sorted(result.missing_labels.items()):
            sample = ", ".join(names[:5])
            more = f" 等 {len(names)} 项" if len(names) > 5 else ""
            lines.append(f"  - 标签 '{label}': {sample}{more}")
    lines.extend(
        [
            "",
            "输出路径:",
            f"  - 数据集目录: {result.yaml_path.parent}",
            f"  - YAML 配置: {result.yaml_path}",
            f"  - 汇总标签: {result.labels_dir}",
        ]
    )
    if preview:
        lines.append("")
        lines.append("预览模式未执行任何写入。")
    return "\n".join(lines)


def _format_split_line(label: str, split: str, image_count: int, stats: dict[str, dict[str, int]]) -> str:
    box_count = sum(stats.get(split, {}).values())
    return f"  - {label}（{split}）: {image_count} 张图片, {box_count} 个标注"
