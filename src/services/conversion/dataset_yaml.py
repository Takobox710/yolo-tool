from __future__ import annotations

from pathlib import Path

from src.services.conversion.types import ConversionConfig


def write_data_yaml(
    config: ConversionConfig, active_splits: tuple[str, ...] | list[str]
) -> Path:
    yaml_path = config.output_dir / "data.yaml"
    split_lines = [
        f"{split}: {config.output_dir.name}/{split}/images"
        for split in ("train", "val", "test")
        if split in active_splits
    ]
    yaml_path.write_text(
        "\n".join(
            [
                f"path: {config.output_dir.parent.as_posix()}",
                *split_lines,
                f"nc: {len(config.class_names)}",
                f"names: {config.class_names}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return yaml_path
