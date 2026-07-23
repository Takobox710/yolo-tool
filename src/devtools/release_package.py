from __future__ import annotations

import argparse
import configparser
import json
import shutil
from pathlib import Path

from src.services.runtime.release_manifest import (
    MANIFEST_SCHEMA_VERSION,
    ReleaseManifestError,
    file_hashes,
)


PACKAGE_TYPES = {"Full", "AppUpdate", "RuntimeFull"}


def _copy_file(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise ReleaseManifestError(f"打包源文件不存在: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _copy_tree(source: Path, destination: Path) -> None:
    if not source.is_dir():
        raise ReleaseManifestError(f"打包源目录不存在: {source}")
    shutil.copytree(source, destination, dirs_exist_ok=True)


def _app_files(app_root: Path, exe_name: str) -> list[str]:
    files = [exe_name]
    assets = app_root / "app_assets"
    if assets.exists():
        files.extend(
            f"app_assets/{path.relative_to(assets).as_posix()}"
            for path in assets.rglob("*")
            if path.is_file()
        )
    return sorted(files)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_package_info(
    path: Path,
    *,
    package_type: str,
    app_version: str,
    runtime_version: str,
    required_runtime_version: str,
) -> None:
    config = configparser.ConfigParser()
    config["Package"] = {
        "type": package_type,
        "app_version": app_version,
        "runtime_version": runtime_version,
        "required_runtime_version": required_runtime_version,
    }
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        config.write(handle)


def build_package(
    app_root: Path,
    output_root: Path,
    *,
    package_type: str,
    app_version: str,
    runtime_version: str,
    required_runtime_version: str,
    exe_name: str = "YOLOTool.exe",
) -> Path:
    if package_type not in PACKAGE_TYPES:
        raise ReleaseManifestError(f"不支持的安装包类型: {package_type}")
    app_root = Path(app_root).resolve()
    output_root = Path(output_root).resolve()
    runtime_root = app_root / "_internal"
    if not (app_root / exe_name).is_file():
        raise ReleaseManifestError(f"PyInstaller 产物缺少 {exe_name}")
    if not runtime_root.is_dir():
        raise ReleaseManifestError("PyInstaller 产物缺少 _internal 运行环境")

    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    app_paths = _app_files(app_root, exe_name) if (app_root / exe_name).is_file() else []
    app_hashes = file_hashes(app_root, app_paths)
    runtime_hashes = file_hashes(runtime_root)

    if package_type in {"Full", "AppUpdate", "RuntimeFull"}:
        _copy_file(app_root / exe_name, output_root / exe_name)
        if (app_root / "app_assets").exists():
            _copy_tree(app_root / "app_assets", output_root / "app_assets")

    if package_type in {"Full", "RuntimeFull"}:
        _copy_tree(runtime_root, output_root / "_internal")

    if package_type == "Full":
        for relative in ("data/models", "images", "labels"):
            source = app_root / relative
            if source.exists():
                _copy_tree(source, output_root / relative)
        runtime = app_root / "data/runtime"
        if runtime.exists():
            _copy_tree(runtime, output_root / "data/runtime")
        result = app_root / "result"
        if result.exists():
            _copy_tree(result, output_root / "result")

    release_manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "app_version": app_version,
        "runtime_version": runtime_version,
        "required_runtime_version": required_runtime_version,
        "app_files": app_hashes,
        "runtime_files": {f"_internal/{key}": value for key, value in runtime_hashes.items()},
    }
    runtime_manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "runtime_version": runtime_version,
        "files": runtime_hashes,
    }
    _write_json(output_root / "release-manifest.json", release_manifest)
    _write_json(output_root / "runtime-manifest.json", runtime_manifest)
    (output_root / "app-version.txt").write_text(app_version + "\n", encoding="utf-8")
    (output_root / "runtime-version.txt").write_text(runtime_version + "\n", encoding="utf-8")
    _write_package_info(
        output_root / "package-info.ini",
        package_type=package_type,
        app_version=app_version,
        runtime_version=runtime_version,
        required_runtime_version=required_runtime_version,
    )
    return output_root


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build YOLOTool layered package staging files")
    parser.add_argument("--app-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--package-type", choices=sorted(PACKAGE_TYPES), required=True)
    parser.add_argument("--app-version", required=True)
    parser.add_argument("--runtime-version", required=True)
    parser.add_argument("--required-runtime-version", required=True)
    parser.add_argument("--exe-name", default="YOLOTool.exe")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    build_package(
        args.app_root,
        args.output_root,
        package_type=args.package_type,
        app_version=args.app_version,
        runtime_version=args.runtime_version,
        required_runtime_version=args.required_runtime_version,
        exe_name=args.exe_name,
    )


if __name__ == "__main__":
    main()
