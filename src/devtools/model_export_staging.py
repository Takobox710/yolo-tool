from __future__ import annotations

import json
import shutil
import time
from pathlib import Path, PurePosixPath
from typing import Callable

from src.devtools.package_files import print_elapsed
from src.devtools.runtime_package_boundaries import safe_distribution_path
from src.services.model_export import EXPORT_PROTOCOL_VERSION, EXTENSION_PACKAGE_ID, EXTENSION_SCHEMA_VERSION
from src.services.model_export.manifest import ORT_GPU_OVERLAY_DIR, ORT_GPU_OVERLAY_KEY


def relative_files(root: Path) -> list[str]:
    base = Path(root).resolve()
    return sorted(path.relative_to(base).as_posix() for path in base.rglob("*") if path.is_file())


def validate_no_base_overlap(staging_root: Path, base_staging_root: Path) -> None:
    manifest_path = Path(base_staging_root) / "base-package-manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError(f"基础包缺少清单，无法校验扩展边界：{manifest_path}")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    base_files = {PurePosixPath(str(value)).relative_to("_internal").as_posix() for value in payload.get("files", []) if PurePosixPath(str(value)).parts and PurePosixPath(str(value)).parts[0] == "_internal"}
    extension_files = {PurePosixPath(relative).as_posix() for relative in relative_files(Path(staging_root) / "packages")}
    overlap = sorted(base_files & extension_files)
    if overlap:
        preview = ", ".join(overlap[:8])
        suffix = " ..." if len(overlap) > 8 else ""
        raise RuntimeError(f"基础包与附加包存在重复文件：{preview}{suffix}")


def build_model_export_layer(staging_root: Path, *, version: str, base_staging_root: Path | None = None, collect_optional: Callable[[Path], dict[str, str]], collect_overlays: Callable[[Path], dict[str, str]]) -> Path:
    staging_root = Path(staging_root).resolve()
    if staging_root.exists():
        shutil.rmtree(staging_root)
    package_root = staging_root / "packages"
    package_root.mkdir(parents=True)
    started = time.perf_counter()
    versions = collect_optional(package_root)
    versions.update(collect_overlays(package_root))
    print_elapsed("[Extra] 运行库文件复制完成", started, perf_counter=time.perf_counter)
    if base_staging_root is not None:
        validate_no_base_overlap(staging_root, Path(base_staging_root).resolve())
    started = time.perf_counter()
    files = [f"packages/{relative}" for relative in relative_files(package_root)]
    print_elapsed("[Extra] 文件清单生成完成", started, perf_counter=time.perf_counter)
    dll_dirs = sorted({str(Path(relative).parent).replace("\\", "/") for relative in files if Path(relative).suffix.lower() in {".dll", ".pyd"}})
    manifest = {"schema_version": EXTENSION_SCHEMA_VERSION, "package_id": EXTENSION_PACKAGE_ID, "protocol_version": EXPORT_PROTOCOL_VERSION, "version": version, "platform": "win-64", "architecture": "x86_64", "package_dir": "packages", "supported_formats": ["openvino", "engine", "ncnn"], "dependencies": versions, "runtime_overlays": {ORT_GPU_OVERLAY_KEY: ORT_GPU_OVERLAY_DIR}, "dll_dirs": dll_dirs, "files": files}
    manifest_path = staging_root / "extension-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest_path


__all__ = ["build_model_export_layer", "relative_files", "validate_no_base_overlap"]
