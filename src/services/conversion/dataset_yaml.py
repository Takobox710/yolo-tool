from __future__ import annotations

from pathlib import Path

from src.services.conversion.types import ConversionConfig


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
