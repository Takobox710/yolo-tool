from __future__ import annotations

import configparser
import hashlib
import os
from pathlib import Path

from src.shared.paths import LOCAL_APP_DATA_ROOT, ROOT
from src.services.runtime.metadata import metadata_directory, metadata_path, resolve_metadata_path


INSTALL_INSTANCE_NAME = "install-instance.ini"
INSTANCE_SCHEMA_VERSION = 1


def normalized_install_path(root: str | Path) -> str:
    resolved = str(Path(root).resolve()).replace("/", "\\").rstrip("\\")
    return os.path.normcase(resolved).lower()


def instance_id_for_path(root: str | Path) -> str:
    value = normalized_install_path(root).encode("utf-8")
    return hashlib.md5(value, usedforsecurity=False).hexdigest()


def load_install_instance(root: str | Path = ROOT) -> dict[str, str]:
    parser = configparser.ConfigParser()
    try:
        parser.read(resolve_metadata_path(root, INSTALL_INSTANCE_NAME), encoding="utf-8")
    except (OSError, configparser.Error):
        return {}
    if not parser.has_section("Install"):
        return {}
    return dict(parser.items("Install"))


def installed_instance_id(root: str | Path = ROOT) -> str:
    value = load_install_instance(root).get("instance_id", "").strip().lower()
    if len(value) == 32 and all(character in "0123456789abcdef" for character in value):
        return value
    return instance_id_for_path(root)


def instance_extensions_root(
    root: str | Path = ROOT,
    *,
    local_app_data: str | Path | None = None,
) -> Path:
    del local_app_data
    return Path(root) / "_internal" / "extensions"


def legacy_instance_extensions_root(
    root: str | Path = ROOT,
    *,
    local_app_data: str | Path | None = None,
) -> Path:
    local_root = Path(local_app_data or LOCAL_APP_DATA_ROOT)
    return local_root / "YOLOTool" / "instances" / installed_instance_id(root) / "extensions"


def legacy_extensions_root(local_app_data: str | Path | None = None) -> Path:
    return Path(local_app_data or LOCAL_APP_DATA_ROOT) / "YOLOTool" / "extensions"


def write_install_instance(
    root: str | Path,
    *,
    app_version: str,
    runtime_version: str,
    base_package_version: str,
    model_bundle_version: str = "",
    model_export_version: str = "",
) -> Path:
    root = Path(root)
    metadata_directory(root).mkdir(parents=True, exist_ok=True)
    parser = configparser.ConfigParser()
    parser["Install"] = {
        "schema_version": str(INSTANCE_SCHEMA_VERSION),
        "instance_id": instance_id_for_path(root),
        "app_version": app_version,
        "runtime_version": runtime_version,
        "base_package_version": base_package_version,
        "model_bundle_version": model_bundle_version,
        "model_export_installed": str(bool(model_export_version)).lower(),
        "model_export_version": model_export_version,
    }
    path = metadata_path(root, INSTALL_INSTANCE_NAME)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        parser.write(handle)
    return path


def migrate_legacy_extensions(
    root: str | Path = ROOT,
    *,
    local_app_data: str | Path | None = None,
) -> bool:
    target = instance_extensions_root(root)
    if target.exists():
        return False
    sources = (
        legacy_instance_extensions_root(root, local_app_data=local_app_data),
        legacy_extensions_root(local_app_data),
    )
    source = next((candidate for candidate in sources if candidate.is_dir()), None)
    if source is None:
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    source.replace(target)
    return True
