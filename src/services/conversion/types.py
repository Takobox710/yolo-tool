from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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
    train_ratio: float = 0.8
    val_ratio: float = 0.2
    test_ratio: float = 0.0
    random_seed: int = 42
    line_to_obb: bool = True
    line_half_width: float = 10.0
    backup_existing: bool = True
    backup_yolo_files: bool = False
    class_name_mapping: dict[str, str] | None = None

    def validate(self) -> "ConversionConfig":
        if self.task_mode not in {"obb", "detect"}:
            raise ValueError("task_mode 必须是 obb 或 detect")
        if self.source_format not in {"labelme", "yolo"}:
            raise ValueError("source_format 必须是 labelme 或 yolo")
        ratio_sum = self.train_ratio + self.val_ratio + self.test_ratio
        if round(ratio_sum, 6) != 1.0:
            raise ValueError(
                f"数据集划分比例之和必须为 1.0，当前为 {ratio_sum:.6f}"
            )
        if self.line_half_width <= 0:
            raise ValueError("线宽半径必须大于 0")
        return self


@dataclass
class ConversionPreview:
    labeled_train_count: int
    labeled_val_count: int
    labeled_test_count: int
    total_boxes: int
    unlabeled_count: int
    yaml_path: Path
    output_dir: Path
    labels_dir: Path
    missing_labels: dict[str, list[str]]
    stats: dict[str, dict[str, int]]
    class_names: list[str]


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
    backup_dir: Path | None = None


@dataclass
class ClassMappingRow:
    yolo_name: str
    labelme_names: str
