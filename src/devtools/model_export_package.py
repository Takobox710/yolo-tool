"""Build the additive model-export runtime package.

The public module remains a compatibility façade; collection, staging and
archive mechanics live in focused devtool modules.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from importlib import metadata
from pathlib import Path

from src.devtools.archive_builder import build_7z_archive
from src.devtools.model_export_collector import (
    collect_optional_distributions as _collect_optional_distributions,
    collect_runtime_overlays as _collect_runtime_overlays,
)
from src.devtools.model_export_staging import (
    build_model_export_layer as _build_model_export_layer,
    validate_no_base_overlap as _validate_no_base_overlap,
)
from src.devtools.runtime_package_boundaries import (
    GPU_EXTRA_DISTRIBUTIONS,
    safe_distribution_path,
)


OPTIONAL_DISTRIBUTIONS = GPU_EXTRA_DISTRIBUTIONS
EXTRA_ARCHIVE_VOLUME_BYTES = 1_073_700_000
EXTRA_ARCHIVE_VOLUME_COUNT = 2
MAX_ARCHIVE_VOLUME_BYTES = 1_073_741_824


def _safe_distribution_path(value: object) -> Path | None:
    return safe_distribution_path(value)


def collect_optional_distributions(package_root: Path, distributions: tuple[str, ...] | None = None) -> dict[str, str]:
    return _collect_optional_distributions(package_root, tuple(OPTIONAL_DISTRIBUTIONS if distributions is None else distributions), metadata_module=metadata)


def collect_runtime_overlays(package_root: Path) -> dict[str, str]:
    return _collect_runtime_overlays(package_root, metadata_module=metadata)


def _validate_no_base_overlap(staging_root: Path, base_staging_root: Path) -> None:
    return _validate_no_base_overlap(staging_root, base_staging_root)


def _build_native_archive(staging_root: Path, archive_path: Path, *, split: bool = False) -> Path:
    return build_7z_archive(
        Path(staging_root),
        Path(archive_path),
        split=split,
        volume_bytes=EXTRA_ARCHIVE_VOLUME_BYTES,
        volume_count=EXTRA_ARCHIVE_VOLUME_COUNT,
        error_type=RuntimeError,
        missing_message="未找到 Pixi 提供的 7z 命令，无法构建模型转换附加包。",
        failed_message="7z 模型转换附加包构建失败，退出码：{code}",
        prefix="[Extra] ",
    )


def build_model_export_layer(staging_root: Path, *, version: str, base_staging_root: Path | None = None) -> Path:
    return _build_model_export_layer(
        staging_root,
        version=version,
        base_staging_root=base_staging_root,
        collect_optional=collect_optional_distributions,
        collect_overlays=collect_runtime_overlays,
    )


def build_model_export_archive(staging_root: Path, output_dir: Path, *, version: str, base_staging_root: Path | None = None, split: bool = False) -> Path:
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / f"YOLOTool_ExtraEnv_{version}.7z"
    print("[Extra] 正在准备模型转换运行库 staging...", flush=True)
    build_model_export_layer(staging_root, version=version, base_staging_root=base_staging_root)
    return _build_native_archive(staging_root, archive_path, split=split)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build additive model export layer")
    parser.add_argument("--staging-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--base-staging", type=Path)
    parser.add_argument("--split", action="store_true")
    args = parser.parse_args()
    print(build_model_export_archive(args.staging_root, args.output_dir, version=args.version, base_staging_root=args.base_staging, split=args.split))


if __name__ == "__main__":
    main()
