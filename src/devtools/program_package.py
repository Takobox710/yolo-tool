from __future__ import annotations

import shutil
from pathlib import Path

from src.services.runtime.release_manifest import MANIFEST_SCHEMA_VERSION, ReleaseManifestError, sha256_file
from src.devtools.package_files import copy_file, write_json, write_package_info


PROGRAM_PACKAGE_TYPE = "Program"
LEGACY_PACKAGE_TYPES = {"Full", "AppUpdate", "RuntimeFull"}
PACKAGE_TYPES = {PROGRAM_PACKAGE_TYPE, *LEGACY_PACKAGE_TYPES}


def build_program_package(
    app_root: Path,
    output_root: Path,
    *,
    app_version: str,
    required_runtime_version: str,
    variant: str = "gpu",
    exe_name: str = "YOLOTool.exe",
) -> Path:
    app_root = Path(app_root).resolve()
    output_root = Path(output_root).resolve()
    if not (app_root / exe_name).is_file():
        raise ReleaseManifestError(f"PyInstaller 产物缺少 {exe_name}")
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True)
    copy_file(app_root / exe_name, output_root / exe_name)
    release_manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "app_version": app_version,
        "required_runtime_version": required_runtime_version,
        "variant": variant,
        "app_files": {exe_name: sha256_file(app_root / exe_name)},
    }
    write_json(output_root / "release-manifest.json", release_manifest)
    (output_root / "app-version.txt").write_text(app_version + "\n", encoding="utf-8")
    write_package_info(
        output_root / "program-package-info.ini",
        package_type=PROGRAM_PACKAGE_TYPE,
        app_version=app_version,
        required_runtime_version=required_runtime_version,
        variant=variant,
    )
    return output_root


def build_package(
    app_root: Path,
    output_root: Path,
    *,
    package_type: str,
    app_version: str,
    runtime_version: str,
    required_runtime_version: str,
    variant: str = "gpu",
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
        variant=variant,
        exe_name=exe_name,
    )


__all__ = ["LEGACY_PACKAGE_TYPES", "PACKAGE_TYPES", "PROGRAM_PACKAGE_TYPE", "build_package", "build_program_package"]
