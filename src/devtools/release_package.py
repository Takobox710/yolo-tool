from __future__ import annotations

import argparse
import configparser
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from src.services.runtime.release_manifest import (
    MANIFEST_SCHEMA_VERSION,
    ReleaseManifestError,
    file_hashes,
)


PROGRAM_PACKAGE_TYPE = "Program"
LEGACY_PACKAGE_TYPES = {"Full", "AppUpdate", "RuntimeFull"}
PACKAGE_TYPES = {PROGRAM_PACKAGE_TYPE, *LEGACY_PACKAGE_TYPES}
BASE_PACKAGE_SCHEMA_VERSION = 1
BASE_PACKAGE_ID = "yolo-tool-base-runtime-models"
BASE_MANIFEST_NAME = "base-package-manifest.json"
MANAGED_MODELS_NAME = "managed-models.json"
BASE_MODEL_NAMES = ("yolo11s.pt", "yolo26n.pt", "yolov8n.pt")
STDLIB_ARCHIVE_NAME = "python_stdlib.zip"


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
    return [exe_name]


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
    required_runtime_version: str,
) -> None:
    config = configparser.ConfigParser()
    config["Package"] = {
        "type": package_type,
        "app_version": app_version,
        "required_runtime_version": required_runtime_version,
    }
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        config.write(handle)


def _build_standard_library_archive(destination: Path) -> None:
    """Add source modules dynamically imported by external frozen packages."""
    stdlib_root = Path(sys.prefix) / "Lib"
    if not stdlib_root.is_dir():
        raise ReleaseManifestError(f"Python 标准库目录不存在: {stdlib_root}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    skip_parts = {
        "test",
        "tests",
        "tkinter",
        "idlelib",
        "lib2to3",
        "site-packages",
    }
    with zipfile.ZipFile(
        destination,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for source in sorted(stdlib_root.rglob("*.py")):
            relative = source.relative_to(stdlib_root)
            if any(part in skip_parts for part in relative.parts):
                continue
            archive.write(source, relative.as_posix())


def _copy_third_party_python_sources(runtime_root: Path) -> None:
    """Restore pure package files that PyInstaller normally embeds in PYZ."""
    site_packages = Path(sys.prefix) / "Lib" / "site-packages"
    if not site_packages.is_dir():
        raise ReleaseManifestError(f"第三方包目录不存在: {site_packages}")
    skip_parts = {"test", "tests", "SelfTest", "__pycache__"}
    for source in sorted(site_packages.rglob("*.py")):
        relative = source.relative_to(site_packages)
        if any(part in skip_parts for part in relative.parts):
            continue
        destination = runtime_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def build_program_package(
    app_root: Path,
    output_root: Path,
    *,
    app_version: str,
    required_runtime_version: str,
    exe_name: str = "YOLOTool.exe",
) -> Path:
    app_root = Path(app_root).resolve()
    output_root = Path(output_root).resolve()
    if not (app_root / exe_name).is_file():
        raise ReleaseManifestError(f"PyInstaller 产物缺少 {exe_name}")

    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True)

    _copy_file(app_root / exe_name, output_root / exe_name)
    release_manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "app_version": app_version,
        "required_runtime_version": required_runtime_version,
        "app_files": file_hashes(app_root, _app_files(app_root, exe_name)),
    }
    _write_json(output_root / "release-manifest.json", release_manifest)
    (output_root / "app-version.txt").write_text(app_version + "\n", encoding="utf-8")
    _write_package_info(
        output_root / "program-package-info.ini",
        package_type=PROGRAM_PACKAGE_TYPE,
        app_version=app_version,
        required_runtime_version=required_runtime_version,
    )
    return output_root


def build_base_runtime_layer(
    app_root: Path,
    staging_root: Path,
    *,
    package_version: str,
    runtime_version: str,
) -> Path:
    app_root = Path(app_root).resolve()
    staging_root = Path(staging_root).resolve()
    runtime_root = app_root / "_internal"
    if not runtime_root.is_dir():
        raise ReleaseManifestError("PyInstaller 产物缺少 _internal 运行环境")
    if staging_root.exists():
        shutil.rmtree(staging_root)
    staging_root.mkdir(parents=True)

    _copy_tree(runtime_root, staging_root / "_internal")
    if (runtime_root / "base_library.zip").is_file():
        _copy_third_party_python_sources(staging_root / "_internal")
        _build_standard_library_archive(
            staging_root / "_internal" / STDLIB_ARCHIVE_NAME
        )
    model_source = app_root / "data" / "models"
    required_model = model_source / "yolo26n.pt"
    if not required_model.is_file():
        raise ReleaseManifestError("PyInstaller 产物缺少 data/models/yolo26n.pt")
    target_models = staging_root / "data" / "models"
    target_models.mkdir(parents=True, exist_ok=True)
    for model_name in BASE_MODEL_NAMES:
        model_path = model_source / model_name
        if not model_path.is_file():
            raise ReleaseManifestError(
                f"基础模型包缺少 data/models/{model_name}"
            )
        _copy_file(model_path, target_models / model_name)

    runtime_hashes = file_hashes(staging_root / "_internal")
    runtime_manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "runtime_version": runtime_version,
        "files": runtime_hashes,
    }
    _write_json(staging_root / "runtime-manifest.json", runtime_manifest)

    models_root = staging_root / "data" / "models"
    model_hashes = file_hashes(models_root) if models_root.is_dir() else {}
    managed_models = {
        "schema_version": 1,
        "files": model_hashes,
    }
    _write_json(staging_root / MANAGED_MODELS_NAME, managed_models)

    payload_paths = [
        path.relative_to(staging_root).as_posix()
        for path in staging_root.rglob("*")
        if path.is_file() and path.name != BASE_MANIFEST_NAME
    ]
    payload_hashes = file_hashes(staging_root, payload_paths)
    unpacked_size = sum(
        (staging_root / Path(relative)).stat().st_size for relative in payload_hashes
    )
    manifest = {
        "schema_version": BASE_PACKAGE_SCHEMA_VERSION,
        "package_id": BASE_PACKAGE_ID,
        "version": package_version,
        "runtime_version": runtime_version,
        "platform": "win-64",
        "architecture": "x86_64",
        "uncompressed_size": unpacked_size,
        "files": payload_hashes,
    }
    manifest_path = staging_root / BASE_MANIFEST_NAME
    _write_json(manifest_path, manifest)
    return manifest_path


def build_base_runtime_archive(
    app_root: Path,
    staging_root: Path,
    output_dir: Path,
    *,
    package_version: str,
    runtime_version: str,
) -> Path:
    staging_root = Path(staging_root).resolve()
    output_dir = Path(output_dir).resolve()
    build_base_runtime_layer(
        app_root,
        staging_root,
        package_version=package_version,
        runtime_version=runtime_version,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / f"YOLOTool_BaseEnv_{package_version}.7z"
    archive_path.unlink(missing_ok=True)
    seven_zip = shutil.which("7z") or shutil.which("7z.exe")
    if not seven_zip:
        raise ReleaseManifestError("未找到 Pixi 提供的 7z 命令，无法构建基础环境包。")
    completed = subprocess.run(
        [
            seven_zip,
            "a",
            "-t7z",
            str(archive_path),
            "*",
            "-m0=lzma2",
            "-mx=9",
            "-ms=off",
            "-mmt=on",
            "-bb0",
            "-bd",
        ],
        cwd=staging_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise ReleaseManifestError(f"7z 基础环境包构建失败: {detail}")
    return archive_path


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
    del runtime_version
    return build_program_package(
        app_root,
        output_root,
        app_version=app_version,
        required_runtime_version=required_runtime_version,
        exe_name=exe_name,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build YOLOTool program package staging")
    parser.add_argument("--app-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--package-type", choices=sorted(PACKAGE_TYPES), default="Program")
    parser.add_argument("--app-version", required=True)
    parser.add_argument("--runtime-version", default="")
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
