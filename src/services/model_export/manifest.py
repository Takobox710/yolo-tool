from __future__ import annotations

import json
import tempfile
from pathlib import Path

import py7zr

from src.services.model_export.native_archive import read_archive_member


EXTENSION_SCHEMA_VERSION = 1
EXPORT_PROTOCOL_VERSION = 1
EXTENSION_PACKAGE_ID = "yolo-tool-model-export-runtime"
PACKAGE_MANIFEST_NAME = "extension-manifest.json"


class ExtensionPackageError(ValueError):
    """Raised when a model export runtime package is invalid."""


def load_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ExtensionPackageError(f"无法读取环境包清单：{path.name}") from exc
    if not isinstance(payload, dict):
        raise ExtensionPackageError(f"环境包清单格式无效：{path.name}")
    return payload


def archive_fingerprint(path: Path) -> tuple[str, int, int]:
    stat_result = path.stat()
    return (str(path.resolve()).lower(), stat_result.st_size, stat_result.st_mtime_ns)


def safe_relative_path(value: str) -> Path:
    normalized = str(value).replace("\\", "/")
    path = Path(normalized)
    if (
        not normalized
        or path.is_absolute()
        or not path.parts
        or ":" in path.parts[0]
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ExtensionPackageError(f"环境包包含不安全路径：{value}")
    return path


def validate_extension_manifest(manifest: dict) -> dict:
    if manifest.get("schema_version") != EXTENSION_SCHEMA_VERSION:
        raise ExtensionPackageError("环境包清单版本不受支持。")
    if manifest.get("package_id") != EXTENSION_PACKAGE_ID:
        raise ExtensionPackageError("选择的文件不是模型转换环境包。")
    if manifest.get("protocol_version") != EXPORT_PROTOCOL_VERSION:
        raise ExtensionPackageError("环境包协议与当前程序不兼容。")
    if manifest.get("platform") != "win-64":
        raise ExtensionPackageError("环境包不是 Windows x64 版本。")
    for key in ("version", "package_dir"):
        if not str(manifest.get(key) or "").strip():
            raise ExtensionPackageError(f"环境包清单缺少字段：{key}")
    safe_relative_path(str(manifest["package_dir"]))
    files = manifest.get("files")
    if isinstance(files, dict):
        manifest = dict(manifest)
        manifest["files"] = list(files)
        files = manifest["files"]
    if not isinstance(files, list) or not files:
        raise ExtensionPackageError("环境包清单没有文件列表。")
    for relative in files:
        safe_relative_path(str(relative))
    dll_dirs = manifest.get("dll_dirs", ())
    if not isinstance(dll_dirs, list):
        raise ExtensionPackageError("环境包 DLL 目录清单无效。")
    for relative in dll_dirs:
        safe_relative_path(str(relative))
    return manifest


def read_7z_manifest(archive_path: Path) -> dict:
    native_manifest = read_archive_member(archive_path, PACKAGE_MANIFEST_NAME)
    if native_manifest is not None:
        try:
            return validate_extension_manifest(
                json.loads(native_manifest.decode("utf-8"))
            )
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ExtensionPackageError(
                "压缩包中的环境包清单不是合法 JSON。"
            ) from exc
    with tempfile.TemporaryDirectory(prefix="yolo-tool-extension-manifest-") as temp:
        try:
            with py7zr.SevenZipFile(archive_path, "r") as archive:
                archive.extract(path=temp, targets=[PACKAGE_MANIFEST_NAME])
            return validate_extension_manifest(
                load_json(Path(temp) / PACKAGE_MANIFEST_NAME)
            )
        except (OSError, py7zr.Bad7zFile) as exc:
            raise ExtensionPackageError("无法读取 7z 环境包清单。") from exc
