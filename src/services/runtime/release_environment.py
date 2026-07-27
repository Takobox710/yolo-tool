from __future__ import annotations

import configparser
import re
import sys
from collections.abc import Callable
from pathlib import Path

from src.services.runtime.release_versions import (
    is_newer_version,
    normalize_environment_version,
)
from src.services.runtime.metadata import resolve_metadata_path
from src.shared.paths import ROOT


_ENVIRONMENT_ASSET_VERSION_PATTERN = re.compile(
    r"^YOLOTool_(BaseEnv|ExtraEnv)_(?P<version>[0-9A-Za-z.-]+)\.(?:7z|zip)$",
    re.IGNORECASE,
)


def has_environment_asset(names: tuple[str, ...], prefix: str) -> bool:
    return any(
        name.casefold().startswith(f"yolotool_{prefix}_") for name in names
    )


def environment_asset_version(names: tuple[str, ...], prefix: str) -> str:
    expected = {"baseenv": "baseenv", "extraenv": "extraenv"}.get(prefix)
    for name in names:
        match = _ENVIRONMENT_ASSET_VERSION_PATTERN.fullmatch(name)
        if match is None or match.group(1).casefold() != expected:
            continue
        return normalize_environment_version(match.group("version"))
    return ""


def installed_environment_versions(
    metadata_loader: Callable[[], dict[str, str]],
) -> tuple[str, str]:
    try:
        metadata = metadata_loader()
    except Exception:
        metadata = {}
    if not isinstance(metadata, dict):
        metadata = {}
    package_metadata = _load_package_metadata()
    base_version = normalize_environment_version(
        metadata.get("base_package_version")
        or package_metadata.get("base_package_version")
    )
    extra_version = normalize_environment_version(
        metadata.get("model_export_version")
        or package_metadata.get("model_export_version")
    )
    if not getattr(sys, "frozen", False):
        base_version = base_version or _read_source_package_version(
            "base-runtime-models-version.txt"
        )
        extra_version = extra_version or _read_source_package_version(
            "model-export-runtime-version.txt"
        )
    if not extra_version:
        try:
            from src.services.model_export import load_installed_extension

            installed = load_installed_extension()
        except Exception:
            installed = None
        if installed is not None:
            extra_version = normalize_environment_version(installed.version)
    return base_version, extra_version


def _load_package_metadata() -> dict[str, str]:
    parser = configparser.ConfigParser()
    try:
        parser.read(
            resolve_metadata_path(ROOT, "package-info.ini"), encoding="utf-8"
        )
    except (OSError, configparser.Error):
        return {}
    if not parser.has_section("Package"):
        return {}
    return dict(parser.items("Package"))


def _read_source_package_version(filename: str) -> str:
    path = Path(ROOT) / "installer" / filename
    try:
        return normalize_environment_version(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        return ""


def environment_update_available(
    remote_version: str,
    installed_version: str,
    asset_exists: bool,
    *,
    missing_is_update: bool = True,
) -> bool | None:
    if not asset_exists:
        return False
    if not remote_version:
        return None
    if not installed_version:
        return missing_is_update
    return is_newer_version(installed_version, remote_version)


__all__ = [
    "environment_asset_version",
    "environment_update_available",
    "has_environment_asset",
    "installed_environment_versions",
]
