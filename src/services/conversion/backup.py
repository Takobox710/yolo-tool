from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from src.services.conversion.types import ConversionConfig


def prepare_output_dirs(config: ConversionConfig) -> Path | None:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    if config.output_dir.exists():
        for split in ("train", "val", "test"):
            split_path = config.output_dir / split
            if split_path.exists():
                shutil.rmtree(split_path)
    if config.labels_dir.exists():
        shutil.rmtree(config.labels_dir)
    config.labels_dir.mkdir(parents=True, exist_ok=True)
    return None


def backup_converted_outputs(config: ConversionConfig, yaml_path: Path) -> Path:
    backup_root = config.output_dir / "old"
    backup_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = backup_root / f"backup-{timestamp}"
    counter = 1
    while backup_dir.exists():
        counter += 1
        backup_dir = backup_root / f"backup-{timestamp}-{counter}"
    labels_backup_dir = backup_dir / "labels"
    labels_backup_dir.mkdir(parents=True, exist_ok=True)
    for label_file in sorted(config.labels_dir.glob("*.txt")):
        shutil.copy2(label_file, labels_backup_dir / label_file.name)
    shutil.copy2(yaml_path, backup_dir / yaml_path.name)
    return backup_dir
