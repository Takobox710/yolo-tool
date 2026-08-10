from __future__ import annotations

import json
import zipfile
from pathlib import Path

from src.services.model_export.manifest import (
    PACKAGE_MANIFEST_NAME,
    ExtensionPackageError,
    archive_fingerprint,
    canonical_7z_volume_path,
    is_7z_archive_path,
    validate_extension_manifest,
)
from src.services.model_export.package_inspection import is_extension_package_path


_MANIFEST_CACHE: dict[tuple[str, int, int], dict] = {}


from src.services.model_export.manifest import read_7z_manifest


def inspect_extension_package_fast(package_path: str | Path) -> dict:
    """Read only the manifest for responsive UI selection dialogs."""
    package_path = canonical_7z_volume_path(Path(package_path))
    if not is_extension_package_path(package_path):
        raise ExtensionPackageError(
            "请选择 .7z、.7z.001 或 .zip 模型转换环境包。"
        )
    try:
        key = archive_fingerprint(package_path)
    except OSError as exc:
        raise ExtensionPackageError(
            "无法读取模型转换环境包信息。"
        ) from exc
    cached = _MANIFEST_CACHE.get(key)
    if cached is not None:
        return cached
    if is_7z_archive_path(package_path):
        manifest = read_7z_manifest(package_path)
    else:
        with zipfile.ZipFile(package_path) as archive:
            try:
                manifest = validate_extension_manifest(
                    json.loads(
                archive.read(PACKAGE_MANIFEST_NAME).decode(
                            "utf-8"
                        )
                    )
                )
            except (KeyError, UnicodeError, json.JSONDecodeError) as exc:
                raise ExtensionPackageError(
                    "压缩包缺少合法的环境包清单。"
                ) from exc
    _MANIFEST_CACHE[key] = manifest
    return manifest
