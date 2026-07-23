from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from src.shared.paths import ROOT


RELEASE_MANIFEST_NAME = "release-manifest.json"
RUNTIME_MANIFEST_NAME = "runtime-manifest.json"
PACKAGE_INFO_NAME = "package-info.ini"
MANIFEST_SCHEMA_VERSION = 1


class ReleaseManifestError(ValueError):
    """Raised when a release or runtime manifest is missing or invalid."""


@dataclass(frozen=True, slots=True)
class RuntimeCompatibility:
    compatible: bool
    runtime_version: str
    required_runtime_version: str
    reason: str


def release_manifest_path(root: Path = ROOT) -> Path:
    return Path(root) / RELEASE_MANIFEST_NAME


def runtime_manifest_path(root: Path = ROOT) -> Path:
    return Path(root) / RUNTIME_MANIFEST_NAME


def _load_json(path: Path) -> dict:
    if not path.exists():
        raise ReleaseManifestError(f"清单文件不存在: {path.name}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReleaseManifestError(f"清单文件无法读取: {path.name}") from exc
    if not isinstance(payload, dict):
        raise ReleaseManifestError(f"清单文件格式无效: {path.name}")
    if payload.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise ReleaseManifestError(f"不支持的清单版本: {path.name}")
    return payload


def load_release_manifest(root: Path = ROOT) -> dict:
    return _load_json(release_manifest_path(root))


def load_runtime_manifest(root: Path = ROOT) -> dict:
    return _load_json(runtime_manifest_path(root))


def installed_runtime_version(root: Path = ROOT) -> str:
    try:
        value = load_runtime_manifest(root).get("runtime_version")
    except ReleaseManifestError:
        return "未登记"
    return str(value) if value else "未登记"


def required_runtime_version(root: Path = ROOT) -> str:
    try:
        release = load_release_manifest(root)
    except ReleaseManifestError:
        return "未登记"
    value = release.get("required_runtime_version")
    return str(value) if value else "未登记"


def check_runtime_compatibility(
    root: Path = ROOT,
    *,
    frozen: bool | None = None,
) -> RuntimeCompatibility:
    is_frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    if not is_frozen:
        return RuntimeCompatibility(True, "开发环境", "开发环境", "开发态跳过发布清单校验")

    try:
        release = load_release_manifest(root)
        runtime = load_runtime_manifest(root)
    except ReleaseManifestError as exc:
        return RuntimeCompatibility(False, "未登记", "未登记", str(exc))

    actual = str(runtime.get("runtime_version") or "")
    required = str(release.get("required_runtime_version") or "")
    if not actual or not required:
        return RuntimeCompatibility(False, actual or "未登记", required or "未登记", "清单缺少运行环境版本")
    if actual != required:
        return RuntimeCompatibility(
            False,
            actual,
            required,
            f"当前运行环境为 {actual}，程序要求 {required}",
        )
    return RuntimeCompatibility(True, actual, required, "运行环境匹配")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_relative_path(value: str) -> str:
    normalized = str(value).replace("\\", "/")
    parts = normalized.split("/")
    if not normalized or normalized.startswith("/") or ":" in parts[0]:
        raise ReleaseManifestError(f"清单路径无效: {value}")
    if any(part in {"", ".", ".."} for part in parts):
        raise ReleaseManifestError(f"清单路径无效: {value}")
    return normalized


def file_hashes(root: Path, relative_paths: Iterable[str] | None = None) -> dict[str, str]:
    base = Path(root).resolve()
    if relative_paths is None:
        paths = [path for path in base.rglob("*") if path.is_file()]
        relative_paths = (path.relative_to(base).as_posix() for path in paths)

    result: dict[str, str] = {}
    for relative in relative_paths:
        normalized = validate_relative_path(relative)
        path = base / Path(normalized)
        if not path.is_file():
            raise ReleaseManifestError(f"清单文件不存在: {normalized}")
        result[normalized] = sha256_file(path)
    return dict(sorted(result.items()))


def verify_file_hashes(root: Path, expected: dict[str, str]) -> tuple[str, ...]:
    failures: list[str] = []
    for relative, expected_hash in expected.items():
        normalized = validate_relative_path(relative)
        path = Path(root) / Path(normalized)
        if not path.is_file() or sha256_file(path) != expected_hash:
            failures.append(normalized)
    return tuple(sorted(failures))
