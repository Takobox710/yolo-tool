from __future__ import annotations

import configparser
import json
import os
import shutil
import stat
import uuid
import zipfile
from pathlib import Path
from typing import Callable

import py7zr

from src.services.model_export.manifest import (
    EXTENSION_PACKAGE_ID,
    EXTENSION_SCHEMA_VERSION,
    EXPORT_PROTOCOL_VERSION,
    PACKAGE_MANIFEST_NAME,
    ExtensionPackageError,
    archive_fingerprint,
    load_json,
    read_7z_manifest,
    safe_relative_path,
    validate_extension_manifest,
)
from src.services.model_export.types import InstalledExtension
from src.services.model_export.archive_extract import (
    ArchiveExtractionError,
    extract_7z,
    extract_zip,
)
from src.services.model_export.probe import probe_packages
from src.services.model_export.verification import verify_installed_extension
from src.services.runtime.install_instance import instance_extensions_root


EXTENSION_DIR_NAME = "model-export-runtime"
ACTIVE_MANIFEST_NAME = "active.json"
PROBE_EXTENSION_ROOT_ENV = "YOLO_TOOL_MODEL_EXPORT_CANDIDATE_ROOT"
_INSPECTION_CACHE: dict[tuple[str, int, int], dict] = {}


def _base_root(base_root: Path | None) -> Path:
    return Path(base_root) if base_root is not None else instance_extensions_root()


def extension_root(base_root: Path | None = None) -> Path:
    return _base_root(base_root) / EXTENSION_DIR_NAME


def _installed_from_manifest(root: Path, manifest: dict) -> InstalledExtension:
    return InstalledExtension(
        version=str(manifest["version"]),
        root=root,
        package_dir=root / Path(manifest["package_dir"]),
        supported_formats=tuple(str(item) for item in manifest.get("supported_formats", ())),
        manifest=manifest,
    )


def load_active_pointer(base_root: Path | None = None) -> dict:
    path = extension_root(base_root) / ACTIVE_MANIFEST_NAME
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_active_pointer(root: Path, payload: dict) -> None:
    root.mkdir(parents=True, exist_ok=True)
    temp = root / f".{ACTIVE_MANIFEST_NAME}.{uuid.uuid4().hex}"
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, root / ACTIVE_MANIFEST_NAME)
    parser = configparser.ConfigParser()
    parser["Extension"] = {
        "active_version": str(payload.get("active_version") or ""),
        "previous_version": str(payload.get("previous_version") or ""),
    }
    with (root / "active.ini").open("w", encoding="utf-8", newline="\n") as handle:
        parser.write(handle)


def load_installed_extension(base_root: Path | None = None) -> InstalledExtension | None:
    root = extension_root(base_root)
    version = str(load_active_pointer(base_root).get("active_version") or "")
    if not version:
        return None
    install_root = root / version
    try:
        installed = load_extension_at(install_root)
    except ExtensionPackageError:
        return None
    return installed if installed.package_dir.is_dir() else None


def load_extension_at(root: Path) -> InstalledExtension:
    root = Path(root)
    manifest = validate_extension_manifest(load_json(root / PACKAGE_MANIFEST_NAME))
    installed = _installed_from_manifest(root, manifest)
    if not installed.package_dir.is_dir():
        raise ExtensionPackageError("模型转换环境缺少 packages 目录。")
    return installed


def install_extension_package(
    package_path: str | Path,
    *,
    base_root: Path | None = None,
    probe: Callable[[Path], dict] = probe_packages,
    progress: Callable[[str, int], None] | None = None,
) -> InstalledExtension:
    package_path = Path(package_path)
    if not package_path.is_file():
        raise ExtensionPackageError("请选择存在的模型转换环境包。")
    suffix = package_path.suffix.lower()
    if suffix not in {".7z", ".zip"}:
        raise ExtensionPackageError("模型转换环境包必须是 .7z 或 .zip 压缩包。")
    return _install_archive_package(
        package_path,
        base_root=_base_root(base_root),
        probe=probe,
        progress=progress,
    )


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
    if package_path.suffix.lower() == ".7z":
        manifest = _inspect_7z(package_path)
    else:
        manifest = _inspect_zip(package_path)
    _INSPECTION_CACHE[key] = manifest
    return manifest


def _install_archive_package(
    archive_path: Path,
    *,
    base_root: Path,
    probe: Callable[[Path], dict],
    progress: Callable[[str, int], None] | None = None,
) -> InstalledExtension:
    root = extension_root(base_root)
    root.mkdir(parents=True, exist_ok=True)
    staging = root / f".install-{uuid.uuid4().hex}"
    staging.mkdir()
    previous = load_active_pointer(base_root)
    try:
        if progress is not None:
            progress("检查压缩包", 5)
        fingerprint = archive_fingerprint(archive_path)
        manifest = inspect_extension_package(archive_path)
        if archive_fingerprint(archive_path) != fingerprint:
            raise ExtensionPackageError("模型转换环境包在安装前发生变化，请重新选择。")
        if progress is not None:
            progress("读取环境包清单", 5)
        try:
            manifest, native_integrity = (
                extract_7z(
                    archive_path,
                    staging,
                    manifest,
                    progress=(
                        None
                        if progress is None
                        else lambda value: progress(
                            "解压附加环境", 5 + int(value * 90 / 100)
                        )
                    ),
                )
                if archive_path.suffix.lower() == ".7z"
                else (extract_zip(archive_path, staging, manifest), False)
            )
        except ArchiveExtractionError as exc:
            raise ExtensionPackageError(str(exc)) from exc
        if progress is not None:
            progress("解压附加环境", 95)
        installed = _installed_from_manifest(staging, manifest)
        if native_integrity:
            if progress is not None:
                progress("原生 7-Zip 完整性校验通过", 97)
        else:
            verify_installed_extension(
                installed,
                progress=(
                    None
                    if progress is None
                    else lambda message, value: progress(
                        message, 95 + int((value - 65) * 2 / 20)
                    )
                ),
                error_factory=ExtensionPackageError,
            )
        if progress is not None:
            progress("探测 TensorRT 环境", 99)
        probe(installed.package_dir)
        result = _promote_candidate(staging, root, manifest, previous)
        if progress is not None:
            progress("完成安装", 100)
        return result
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _promote_candidate(
    candidate_root: Path,
    root: Path,
    manifest: dict,
    previous: dict,
) -> InstalledExtension:
    version = str(manifest["version"])
    target = root / version
    backup = root / f".replace-{uuid.uuid4().hex}"
    replaced_existing = False
    try:
        if target.exists():
            target.replace(backup)
            replaced_existing = True
        candidate_root.replace(target)
        old_active = str(previous.get("active_version") or "")
        old_previous = str(previous.get("previous_version") or "")
        previous_version = old_active if old_active != version else old_previous
        _write_active_pointer(
            root,
            {"active_version": version, "previous_version": previous_version},
        )
        shutil.rmtree(backup, ignore_errors=True)
        _cleanup_old_versions(root, {version, previous_version})
        return _installed_from_manifest(target, manifest)
    except Exception:
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
        if replaced_existing and backup.exists():
            backup.replace(target)
        raise


def _cleanup_old_versions(root: Path, keep: set[str]) -> None:
    for path in root.iterdir():
        if path.is_dir() and not path.name.startswith(".") and path.name not in keep:
            shutil.rmtree(path, ignore_errors=True)
