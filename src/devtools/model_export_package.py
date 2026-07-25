from __future__ import annotations

import argparse
import json
import shutil
from importlib import metadata
from pathlib import Path, PurePosixPath

import py7zr

from src.services.model_export import (
    EXPORT_PROTOCOL_VERSION,
    EXTENSION_PACKAGE_ID,
    EXTENSION_SCHEMA_VERSION,
)
from src.services.runtime.release_manifest import file_hashes


OPTIONAL_DISTRIBUTIONS = (
    "tensorrt",
    "tensorrt-cu13",
    "tensorrt-cu13-libs",
    "tensorrt-cu13-bindings",
)


def _safe_distribution_path(value: object) -> Path | None:
    path = PurePosixPath(str(value).replace("\\", "/"))
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        return None
    return Path(*path.parts)


def collect_optional_distributions(
    package_root: Path,
    distributions: tuple[str, ...] = OPTIONAL_DISTRIBUTIONS,
) -> dict[str, str]:
    package_root = Path(package_root)
    versions: dict[str, str] = {}
    copied: set[Path] = set()
    for name in distributions:
        try:
            distribution = metadata.distribution(name)
        except metadata.PackageNotFoundError as exc:
            raise RuntimeError(f"模型转换环境缺少分发包：{name}") from exc
        versions[name] = distribution.version
        for item in distribution.files or ():
            relative = _safe_distribution_path(item)
            if relative is None:
                continue
            source = Path(distribution.locate_file(item))
            if not source.is_file():
                continue
            target = package_root / relative
            if target in copied:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied.add(target)
    if not copied:
        raise RuntimeError("未收集到模型转换环境文件。")
    return versions


def build_model_export_layer(staging_root: Path, *, version: str) -> Path:
    staging_root = Path(staging_root).resolve()
    if staging_root.exists():
        shutil.rmtree(staging_root)
    package_root = staging_root / "packages"
    package_root.mkdir(parents=True)
    versions = collect_optional_distributions(package_root)
    hashes = {
        f"packages/{relative}": digest
        for relative, digest in file_hashes(package_root).items()
    }
    dll_dirs = sorted(
        {
            str(Path(relative).parent).replace("\\", "/")
            for relative in hashes
            if Path(relative).suffix.lower() in {".dll", ".pyd"}
        }
    )
    manifest = {
        "schema_version": EXTENSION_SCHEMA_VERSION,
        "package_id": EXTENSION_PACKAGE_ID,
        "protocol_version": EXPORT_PROTOCOL_VERSION,
        "version": version,
        "platform": "win-64",
        "architecture": "x86_64",
        "package_dir": "packages",
        "supported_formats": ["engine"],
        "dependencies": versions,
        "dll_dirs": dll_dirs,
        "files": hashes,
    }
    manifest_path = staging_root / "extension-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def build_model_export_archive(
    staging_root: Path,
    output_dir: Path,
    *,
    version: str,
) -> Path:
    staging_root = Path(staging_root).resolve()
    output_dir = Path(output_dir).resolve()
    build_model_export_layer(staging_root, version=version)
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / f"YOLOTool_ExtraEnv_{version}.7z"
    archive_path.unlink(missing_ok=True)
    filters = [
        {
            "id": py7zr.FILTER_LZMA2,
            "preset": 9 | py7zr.PRESET_EXTREME,
        }
    ]
    with py7zr.SevenZipFile(archive_path, "w", filters=filters) as archive:
        for path in sorted(staging_root.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(staging_root).as_posix())
    return archive_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build additive model export layer")
    parser.add_argument("--staging-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    print(
        build_model_export_archive(
            args.staging_root,
            args.output_dir,
            version=args.version,
        )
    )


if __name__ == "__main__":
    main()
