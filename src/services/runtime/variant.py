"""Build and installation variant helpers."""

from __future__ import annotations

import os
import configparser
from pathlib import Path


CPU_VARIANT = "cpu"
GPU_VARIANT = "gpu"
SUPPORTED_VARIANTS = frozenset({CPU_VARIANT, GPU_VARIANT})
BUILD_VARIANT_ENV = "YOLO_TOOL_BUILD_VARIANT"


def normalize_variant(value: object, *, default: str = GPU_VARIANT) -> str:
    normalized = str(value or "").strip().casefold()
    if normalized in SUPPORTED_VARIANTS:
        return normalized
    return default if default in SUPPORTED_VARIANTS else GPU_VARIANT


def build_variant(*, default: str = GPU_VARIANT) -> str:
    return normalize_variant(os.environ.get(BUILD_VARIANT_ENV), default=default)


def installed_variant(root: str | Path | None = None) -> str:
    if root is None:
        from src.shared.paths import ROOT

        root = ROOT
    root = Path(root)
    metadata_root = root / "_internal" / "yolotool_metadata"
    for filename, section in (
        ("package-info.ini", "Package"),
        ("install-instance.ini", "Install"),
    ):
        parser = configparser.ConfigParser()
        try:
            parser.read(metadata_root / filename, encoding="utf-8")
        except (OSError, UnicodeError, configparser.Error):
            continue
        value = parser.get(section, "variant", fallback="")
        if value:
            return normalize_variant(value)
    return build_variant()


def variant_asset_prefix(variant: str) -> str:
    return "YOLOTool_CPU" if normalize_variant(variant) == CPU_VARIANT else "YOLOTool"


def is_cpu_asset_name(name: str) -> bool:
    return str(name or "").casefold().startswith("yolotool_cpu_")


__all__ = [
    "BUILD_VARIANT_ENV",
    "CPU_VARIANT",
    "GPU_VARIANT",
    "SUPPORTED_VARIANTS",
    "build_variant",
    "is_cpu_asset_name",
    "installed_variant",
    "normalize_variant",
    "variant_asset_prefix",
]
