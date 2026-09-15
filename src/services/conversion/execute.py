from __future__ import annotations

import shutil
from collections import defaultdict
from collections.abc import Callable

from src.services.conversion.backup import (
    backup_converted_outputs,
    prepare_output_dirs as _prepare_output_dirs,
)
from src.services.conversion.class_mapping import (
    build_class_mapping_rows,
    detect_class_names,
    detect_labelme_classes,
    normalize_class_name_mapping,
    parse_class_mapping_rows,
)
from src.services.conversion.dataset_split import (
    add_label_stats,
    build_empty_stats,
    collect_inputs,
    split_labeled,
)
from src.services.conversion.dataset_yaml import write_data_yaml
from src.services.conversion.formatting import format_conversion_result
from src.services.conversion.labelme_parser import (
    convert_label_file,
    normalize_points,
    shape_to_detect_bbox,
    shape_to_obb_points,
)
from src.services.conversion.types import (
    ClassMappingRow,
    ConversionConfig,
    ConversionPreview,
    ConversionResult,
)

ProgressCallback = Callable[[str, int], None]


def _report_progress(
    progress: ProgressCallback | None, message: str, value: int
) -> None:
    if progress is not None:
        progress(message, max(0, min(100, int(value))))


def preview_conversion(
    config: ConversionConfig,
    progress: ProgressCallback | None = None,
) -> ConversionPreview:
    _report_progress(progress, "扫描输入文件", 0)
    active = config.validate()
    labeled, unlabeled = collect_inputs(active)
    if not labeled:
        raise ValueError("没有找到可转换的已标注图片")
    _report_progress(progress, "识别类别", 15)
    class_names = detect_class_names(active, labeled)
    active.class_names = class_names
    split_map = split_labeled(labeled, active)
    stats = build_empty_stats()
    missing_labels: defaultdict[str, list[str]] = defaultdict(list)
    total_boxes = 0
    invalid_images: dict[str, str] = {}
    total_items = sum(len(pairs) for pairs in split_map.values())
    processed_items = 0
    _report_progress(progress, "解析标注", 25)
    for split, pairs in split_map.items():
        for _image_path, label_source_path in pairs:
            try:
                lines = _read_output_lines(active, label_source_path, missing_labels)
            except ValueError as exc:
                if active.task_mode != "pose":
                    raise
                invalid_images[label_source_path.name] = str(exc)
                continue
            add_label_stats(
                stats[split],
                lines,
                active.class_names,
                missing_labels,
                label_source_path.name,
            )
            total_boxes += len(lines)
            processed_items += 1
            if total_items:
                _report_progress(
                    progress,
                    "解析标注",
                    25 + int(processed_items * 70 / total_items),
                )
    _report_progress(progress, "预览完成", 100)
    return ConversionPreview(
        labeled_train_count=len(split_map["train"]),
        labeled_val_count=len(split_map["val"]),
        labeled_test_count=len(split_map["test"]),
        total_boxes=total_boxes,
        unlabeled_count=len(unlabeled),
        yaml_path=active.output_dir / "data.yaml",
        output_dir=active.output_dir,
        labels_dir=active.labels_dir,
        missing_labels={key: value[:] for key, value in missing_labels.items()},
        stats={key: dict(value) for key, value in stats.items()},
        class_names=class_names,
        invalid_images=invalid_images,
        keypoint_count=active.pose_keypoint_count,
    )


def run_conversion(
    config: ConversionConfig,
    progress: ProgressCallback | None = None,
) -> ConversionResult:
    _report_progress(progress, "扫描输入文件", 0)
    active = config.validate()
    if active.task_mode == "pose":
        preview = preview_conversion(
            active,
            progress=(
                None
                if progress is None
                else lambda message, value: _report_progress(
                    progress, message, int(value * 0.2)
                )
            ),
        )
        if preview.invalid_images:
            details = "; ".join(
                f"{name}: {reason}" for name, reason in sorted(preview.invalid_images.items())
            )
            raise ValueError(f"Pose 转换校验失败，未写入任何文件：{details}")
    labeled, unlabeled = collect_inputs(active)
    if not labeled:
        raise ValueError("没有找到可转换的已标注图片")
    _report_progress(progress, "识别类别", 20)
    class_names = detect_class_names(active, labeled)
    active.class_names = class_names
    split_map = split_labeled(labeled, active)
    _report_progress(progress, "准备输出目录", 25)
    backup_dir = _prepare_output_dirs(active)
    active_splits = tuple(split for split, pairs in split_map.items() if pairs)

    stats = build_empty_stats()
    missing_labels: defaultdict[str, list[str]] = defaultdict(list)
    total_boxes = 0
    total_items = sum(len(pairs) for pairs in split_map.values())
    processed_items = 0
    _report_progress(progress, "写入数据集", 30)
    for split, pairs in split_map.items():
        if not pairs:
            continue
        split_dir = active.output_dir / split
        (split_dir / "images").mkdir(parents=True, exist_ok=True)
        (split_dir / "labels").mkdir(parents=True, exist_ok=True)
        for image_path, label_source_path in pairs:
            shutil.copy2(image_path, split_dir / "images" / image_path.name)
            lines = _read_output_lines(active, label_source_path, missing_labels)
            label_text = "\n".join(lines) + ("\n" if lines else "")
            target_label_path = split_dir / "labels" / f"{image_path.stem}.txt"
            target_label_path.write_text(label_text, encoding="utf-8")
            shutil.copy2(target_label_path, active.labels_dir / target_label_path.name)
            add_label_stats(
                stats[split],
                lines,
                active.class_names,
                missing_labels,
                label_source_path.name,
            )
            total_boxes += len(lines)
            processed_items += 1
            if total_items:
                _report_progress(
                    progress,
                    "写入数据集",
                    30 + int(processed_items * 65 / total_items),
                )

    _report_progress(progress, "生成 data.yaml", 96)
    yaml_path = write_data_yaml(active, active_splits)
    if active.backup_yolo_files:
        _report_progress(progress, "备份标注文件", 98)
        backup_dir = backup_converted_outputs(active, yaml_path)
    _report_progress(progress, "划分完成", 100)
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
        backup_dir=backup_dir,
        keypoint_count=active.pose_keypoint_count,
    )


def _read_output_lines(
    config: ConversionConfig,
    label_source_path,
    missing_labels: dict[str, list[str]],
) -> list[str]:
    if config.source_format == "labelme":
        return convert_label_file(label_source_path, config, missing_labels)
    label_text = label_source_path.read_text(encoding="utf-8")
    lines = [line.strip() for line in label_text.splitlines() if line.strip()]
    if config.task_mode == "pose":
        from src.services.conversion.pose import validate_pose_yolo_lines

        keypoint_count = validate_pose_yolo_lines(lines)
        if keypoint_count is not None:
            if config.pose_keypoint_count is None:
                config.pose_keypoint_count = keypoint_count
            elif config.pose_keypoint_count != keypoint_count:
                raise ValueError(
                    f"{label_source_path.name} 的关键点数量为 {keypoint_count}，与数据集要求 {config.pose_keypoint_count} 不一致"
                )
    return lines
