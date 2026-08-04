from __future__ import annotations

import json
import stat
import zipfile
from pathlib import Path

import py7zr

from src.services.model_export.manifest import (
    PACKAGE_MANIFEST_NAME,
    ExtensionPackageError,
    archive_fingerprint,
    read_7z_manifest,
    safe_relative_path,
    validate_extension_manifest,
)

_INSPECTION_CACHE: dict[tuple[str, int, int], dict] = {}


def is_extension_package_path(path: str | Path) -> bool:
    value = Path(path)
    return value.is_file() and value.suffix.lower() in {".7z", ".zip"}


def _is_zip_symlink(info: zipfile.ZipInfo) -> bool:
    return stat.S_IFMT(info.external_attr >> 16) == stat.S_IFLNK


def _inspect_zip(archive_path: Path) -> dict:
    with zipfile.ZipFile(archive_path) as archive:
        try:
            manifest = validate_extension_manifest(
                json.loads(archive.read(PACKAGE_MANIFEST_NAME).decode("utf-8"))
            )
        except (KeyError, UnicodeError, json.JSONDecodeError) as exc:
            raise ExtensionPackageError("压缩包缺少合法的环境包清单。") from exc
        expected = set(manifest["files"])
        seen: set[str] = set()
        for info in archive.infolist():
            relative = info.filename.replace("\\", "/").rstrip("/")
            if not relative:
                continue
            safe_relative_path(relative)
            if _is_zip_symlink(info):
                raise ExtensionPackageError(f"环境包不允许符号链接：{relative}")
            if info.is_dir():
                continue
            if relative != PACKAGE_MANIFEST_NAME and relative not in expected:
                raise ExtensionPackageError(f"环境包包含未登记文件：{relative}")
            if relative in seen:
                raise ExtensionPackageError(f"环境包包含重复文件：{relative}")
            seen.add(relative)
        missing = expected - seen
        if missing:
            raise ExtensionPackageError(f"环境包缺少文件：{sorted(missing)[0]}")
        return manifest


def _inspect_7z(archive_path: Path, manifest: dict | None = None) -> dict:
    try:
        with py7zr.SevenZipFile(archive_path, "r") as archive:
            infos = archive.list()
    except (OSError, py7zr.Bad7zFile) as exc:
        raise ExtensionPackageError("无法读取 7z 模型转换环境包。") from exc
    names: set[str] = set()
    for info in infos:
        relative = str(info.filename).replace("\\", "/").rstrip("/")
        if not relative:
            continue
        safe_relative_path(relative)
        if info.is_symlink:
            raise ExtensionPackageError(f"环境包不允许符号链接：{relative}")
        if info.is_directory:
            continue
        if relative in names:
            raise ExtensionPackageError(f"环境包包含重复文件：{relative}")
        names.add(relative)
    if PACKAGE_MANIFEST_NAME not in names:
        raise ExtensionPackageError("压缩包缺少合法的环境包清单。")
    manifest = manifest or read_7z_manifest(archive_path)
    expected = set(manifest["files"])
    extra = names - expected - {PACKAGE_MANIFEST_NAME}
    if extra:
        raise ExtensionPackageError(f"环境包包含未登记文件：{sorted(extra)[0]}")
    missing = expected - names
    if missing:
        raise ExtensionPackageError(f"环境包缺少文件：{sorted(missing)[0]}")
    return manifest


def inspect_extension_package(package_path: str | Path) -> dict:
    package_path = Path(package_path)
    if not is_extension_package_path(package_path):
        raise ExtensionPackageError("请选择 .7z 或 .zip 模型转换环境包。")
    try:
        key = archive_fingerprint(package_path)
    except OSError as exc:
        raise ExtensionPackageError("无法读取模型转换环境包信息。") from exc
    cached = _INSPECTION_CACHE.get(key)
    if cached is not None:
        return cached
    manifest = (
        _inspect_7z(package_path)
        if package_path.suffix.lower() == ".7z"
        else _inspect_zip(package_path)
    )
    _INSPECTION_CACHE[key] = manifest
    return manifest
