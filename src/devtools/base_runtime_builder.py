"""Compatibility façade for Base runtime staging and archive construction."""

from __future__ import annotations

from importlib import metadata
from pathlib import Path

from src.devtools.archive_builder import build_7z_archive
from src.devtools import base_runtime_dependencies as _dependencies
from src.devtools.base_runtime_spec import (
    BASE_ARCHIVE_VOLUME_BYTES,
    BASE_ARCHIVE_VOLUME_COUNT,
    BASE_MANIFEST_NAME,
    BASE_MODEL_NAMES,
    BASE_PACKAGE_ID,
    BASE_PACKAGE_SCHEMA_VERSION,
    CPU_BASE_MODEL_NAMES,
    GPU_BASE_MODEL_NAMES,
    MANAGED_MODELS_NAME,
    STDLIB_ARCHIVE_NAME,
    base_model_names_for_variant,
)
from src.devtools.base_runtime_staging import build_base_runtime_layer as _build_base_runtime_layer, build_standard_library_archive
from src.devtools.runtime_package_boundaries import extension_distribution_paths
from src.services.runtime.release_manifest import ReleaseManifestError
from src.services.runtime.variant import normalize_variant, variant_asset_prefix


def build_base_runtime_archive(
    app_root: Path,
    staging_root: Path,
    output_dir: Path,
    *,
    package_version: str,
    runtime_version: str,
    variant: str = "gpu",
    split: bool = False,
    cpu_runtime_root: Path | None = None,
) -> Path:
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    variant = normalize_variant(variant)
    archive_path = output_dir / f"{variant_asset_prefix(variant)}_BaseEnv_{package_version}.7z"
    build_base_runtime_layer(app_root, staging_root, package_version=package_version, runtime_version=runtime_version, variant=variant, cpu_runtime_root=cpu_runtime_root)
    return build_7z_archive(
        Path(staging_root),
        archive_path,
        split=split,
        volume_bytes=BASE_ARCHIVE_VOLUME_BYTES,
        volume_count=BASE_ARCHIVE_VOLUME_COUNT,
        error_type=ReleaseManifestError,
        missing_message="未找到 Pixi 提供的 7z 命令，无法构建基础环境包。",
        failed_message="7z 基础环境包构建失败，退出码：{code}",
        prefix="[Base] ",
    )


def build_base_runtime_layer(*args, **kwargs):
    _dependencies.extension_distribution_paths = extension_distribution_paths
    return _build_base_runtime_layer(*args, **kwargs)


__all__ = [
    "BASE_MANIFEST_NAME",
    "BASE_MODEL_NAMES",
    "CPU_BASE_MODEL_NAMES",
    "GPU_BASE_MODEL_NAMES",
    "BASE_PACKAGE_ID",
    "BASE_PACKAGE_SCHEMA_VERSION",
    "BASE_ARCHIVE_VOLUME_BYTES",
    "BASE_ARCHIVE_VOLUME_COUNT",
    "MANAGED_MODELS_NAME",
    "STDLIB_ARCHIVE_NAME",
    "build_base_runtime_archive",
    "build_base_runtime_layer",
    "build_standard_library_archive",
    "base_model_names_for_variant",
]
