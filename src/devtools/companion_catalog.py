from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import py7zr

from src.devtools.release_package import (
    BASE_MANIFEST_NAME,
    BASE_PACKAGE_ID,
    BASE_PACKAGE_SCHEMA_VERSION,
)
from src.services.model_export import inspect_extension_package
from src.services.runtime.variant import normalize_variant


def archive_uncompressed_size(path: Path) -> int:
    with py7zr.SevenZipFile(path, "r") as archive:
        return sum(
            int(item.uncompressed or 0)
            for item in archive.list()
            if not item.is_directory
        )


def inspect_base_archive(path: Path, *, expected_variant: str | None = None) -> dict:
    path = Path(path).resolve()
    if path.name.casefold().endswith(".7z.001"):
        seven_zip = shutil.which("7z") or shutil.which("7z.exe")
        if not seven_zip:
            raise ValueError("读取基础环境分卷需要原生 7-Zip。")
        completed = subprocess.run(
            [seven_zip, "e", "-so", "-bso0", "-bsp0", "-bb0", str(path), BASE_MANIFEST_NAME],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if completed.returncode != 0:
            raise ValueError("基础环境分卷无法由 7-Zip 读取。")
        manifest = json.loads(completed.stdout.decode("utf-8"))
    else:
        with tempfile.TemporaryDirectory(prefix="yolo-tool-base-manifest-") as temp:
            with py7zr.SevenZipFile(path, "r") as archive:
                archive.extract(path=temp, targets=[BASE_MANIFEST_NAME])
            manifest = json.loads(
                (Path(temp) / BASE_MANIFEST_NAME).read_text(encoding="utf-8")
            )
    return _base_catalog_entry(
        manifest,
        filename=path.name,
        expected_variant=expected_variant,
    )


def inspect_base_staging(path: Path, *, expected_variant: str | None = None) -> dict:
    path = Path(path).resolve()
    manifest_path = path / BASE_MANIFEST_NAME
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("基础运行时 staging 缺少有效基础包清单。") from exc
    return _base_catalog_entry(
        manifest,
        filename="",
        expected_variant=expected_variant,
        integrated=True,
    )


def _base_catalog_entry(
    manifest: dict,
    *,
    filename: str,
    expected_variant: str | None = None,
    integrated: bool = False,
) -> dict:
    if manifest.get("schema_version") != BASE_PACKAGE_SCHEMA_VERSION:
        raise ValueError("基础环境包清单版本不受支持。")
    if manifest.get("package_id") != BASE_PACKAGE_ID:
        raise ValueError("选择的文件不是 YOLOTool 基础环境和模型包。")
    if manifest.get("platform") != "win-64":
        raise ValueError("基础环境包不是 Windows x64 版本。")
    variant = normalize_variant(manifest.get("variant"))
    if expected_variant is not None and variant != normalize_variant(expected_variant):
        raise ValueError(
            f"基础环境包变体 '{variant}' 与要求的变体 '{normalize_variant(expected_variant)}' 不一致。"
        )
    return {
        "filename": filename,
        "integrated": integrated,
        "package_id": str(manifest["package_id"]),
        "manifest_schema": int(manifest["schema_version"]),
        "platform": str(manifest["platform"]),
        "architecture": str(manifest["architecture"]),
        "version": str(manifest["version"]),
        "runtime_version": str(manifest["runtime_version"]),
        "variant": variant,
        "uncompressed_size": int(manifest["uncompressed_size"]),
    }


def build_companion_catalog(
    base_archive: Path | None = None,
    extension_archive: Path | None = None,
    *,
    variant: str = "gpu",
    base_staging: Path | None = None,
) -> dict:
    variant = normalize_variant(variant)
    if (base_archive is None) == (base_staging is None):
        raise ValueError("必须且只能提供基础环境归档或基础运行时 staging。")
    payload = {
        "schema_version": 1,
        "base": (
            inspect_base_archive(base_archive, expected_variant=variant)
            if base_archive is not None
            else inspect_base_staging(base_staging, expected_variant=variant)
        ),
    }
    if extension_archive is not None:
        extension_archive = Path(extension_archive).resolve()
        manifest = inspect_extension_package(extension_archive)
        payload["model_export"] = {
            "filename": extension_archive.name,
            "package_id": str(manifest["package_id"]),
            "manifest_schema": int(manifest["schema_version"]),
            "platform": str(manifest["platform"]),
            "architecture": str(manifest["architecture"]),
            "version": str(manifest["version"]),
            "protocol_version": int(manifest["protocol_version"]),
            "uncompressed_size": archive_uncompressed_size(extension_archive),
        }
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build installer companion catalog")
    base_group = parser.add_mutually_exclusive_group(required=True)
    base_group.add_argument("--base", type=Path)
    base_group.add_argument("--base-staging", type=Path)
    parser.add_argument("--extension", type=Path)
    parser.add_argument("--variant", default="gpu")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build_companion_catalog(
        args.base,
        args.extension,
        variant=args.variant,
        base_staging=args.base_staging,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output)


if __name__ == "__main__":
    main()
