from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

import py7zr

from src.devtools.release_package import (
    BASE_MANIFEST_NAME,
    BASE_PACKAGE_ID,
    BASE_PACKAGE_SCHEMA_VERSION,
)
from src.services.model_export import inspect_extension_package
from src.services.runtime.release_manifest import sha256_file


def archive_uncompressed_size(path: Path) -> int:
    with py7zr.SevenZipFile(path, "r") as archive:
        return sum(
            int(item.uncompressed or 0)
            for item in archive.list()
            if not item.is_directory
        )


def inspect_base_archive(path: Path) -> dict:
    path = Path(path).resolve()
    with tempfile.TemporaryDirectory(prefix="yolo-tool-base-manifest-") as temp:
        with py7zr.SevenZipFile(path, "r") as archive:
            archive.extract(path=temp, targets=[BASE_MANIFEST_NAME])
        manifest = json.loads(
            (Path(temp) / BASE_MANIFEST_NAME).read_text(encoding="utf-8")
        )
    if manifest.get("schema_version") != BASE_PACKAGE_SCHEMA_VERSION:
        raise ValueError("基础环境包清单版本不受支持。")
    if manifest.get("package_id") != BASE_PACKAGE_ID:
        raise ValueError("选择的文件不是 YOLOTool 基础环境和模型包。")
    if manifest.get("platform") != "win-64":
        raise ValueError("基础环境包不是 Windows x64 版本。")
    return {
        "filename": path.name,
        "package_id": str(manifest["package_id"]),
        "manifest_schema": int(manifest["schema_version"]),
        "platform": str(manifest["platform"]),
        "architecture": str(manifest["architecture"]),
        "sha256": sha256_file(path),
        "compressed_size": path.stat().st_size,
        "version": str(manifest["version"]),
        "runtime_version": str(manifest["runtime_version"]),
        "uncompressed_size": int(manifest["uncompressed_size"]),
    }


def build_companion_catalog(
    base_archive: Path,
    extension_archive: Path | None = None,
) -> dict:
    payload = {"schema_version": 1, "base": inspect_base_archive(base_archive)}
    if extension_archive is not None:
        extension_archive = Path(extension_archive).resolve()
        manifest = inspect_extension_package(extension_archive)
        payload["model_export"] = {
            "filename": extension_archive.name,
            "package_id": str(manifest["package_id"]),
            "manifest_schema": int(manifest["schema_version"]),
            "platform": str(manifest["platform"]),
            "architecture": str(manifest["architecture"]),
            "sha256": sha256_file(extension_archive),
            "compressed_size": extension_archive.stat().st_size,
            "version": str(manifest["version"]),
            "protocol_version": int(manifest["protocol_version"]),
            "uncompressed_size": archive_uncompressed_size(extension_archive),
        }
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build installer companion catalog")
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--extension", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build_companion_catalog(args.base, args.extension)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output)


if __name__ == "__main__":
    main()
