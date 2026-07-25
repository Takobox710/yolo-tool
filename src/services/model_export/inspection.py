from __future__ import annotations

import json
import zipfile
from pathlib import Path

from src.services.model_export.manifest import (
    PACKAGE_MANIFEST_NAME,
    ExtensionPackageError,
    archive_fingerprint,
    validate_extension_manifest,
)


_MANIFEST_CACHE: dict[tuple[str, int, int], dict] = {}


from src.services.model_export.manifest import read_7z_manifest


def inspect_extension_package_fast(package_path: str | Path) -> dict:
    """Read only the manifest for responsive UI selection dialogs."""
    package_path = Path(package_path)
    if not package_path.is_file() or package_path.suffix.lower() not in {".7z", ".zip"}:
        raise ExtensionPackageError(
            "请选择 .7z 或 .zip 模型转换环境包。"
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
    if package_path.suffix.lower() == ".7z":
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
