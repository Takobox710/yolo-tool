from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path

import py7zr

from src.services.model_export import package as package_service
from src.services.model_export.native_archive import read_archive_member


_MANIFEST_CACHE: dict[tuple[str, int, int], dict] = {}


def _read_7z_manifest(archive_path: Path) -> dict:
    native_manifest = read_archive_member(
        archive_path, package_service.PACKAGE_MANIFEST_NAME
    )
    if native_manifest is not None:
        try:
            return package_service.validate_extension_manifest(
                json.loads(native_manifest.decode("utf-8"))
            )
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise package_service.ExtensionPackageError(
                "压缩包中的环境包清单不是合法 JSON。"
            ) from exc
    with tempfile.TemporaryDirectory(prefix="yolo-tool-extension-manifest-") as temp:
        try:
            with py7zr.SevenZipFile(archive_path, "r") as archive:
                archive.extract(path=temp, targets=[package_service.PACKAGE_MANIFEST_NAME])
            return package_service.validate_extension_manifest(
                package_service._load_json(
                    Path(temp) / package_service.PACKAGE_MANIFEST_NAME
                )
            )
        except (OSError, py7zr.Bad7zFile) as exc:
            raise package_service.ExtensionPackageError(
                "无法读取 7z 环境包清单。"
            ) from exc


def inspect_extension_package_fast(package_path: str | Path) -> dict:
    """Read only the manifest for responsive UI selection dialogs."""
    package_path = Path(package_path)
    if not package_service.is_extension_package_path(package_path):
        raise package_service.ExtensionPackageError(
            "请选择 .7z 或 .zip 模型转换环境包。"
        )
    try:
        key = package_service._archive_fingerprint(package_path)
    except OSError as exc:
        raise package_service.ExtensionPackageError(
            "无法读取模型转换环境包信息。"
        ) from exc
    cached = _MANIFEST_CACHE.get(key)
    if cached is not None:
        return cached
    if package_path.suffix.lower() == ".7z":
        manifest = _read_7z_manifest(package_path)
    else:
        with zipfile.ZipFile(package_path) as archive:
            try:
                manifest = package_service.validate_extension_manifest(
                    json.loads(
                        archive.read(package_service.PACKAGE_MANIFEST_NAME).decode(
                            "utf-8"
                        )
                    )
                )
            except (KeyError, UnicodeError, json.JSONDecodeError) as exc:
                raise package_service.ExtensionPackageError(
                    "压缩包缺少合法的环境包清单。"
                ) from exc
    _MANIFEST_CACHE[key] = manifest
    return manifest
