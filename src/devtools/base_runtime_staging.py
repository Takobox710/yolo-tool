from __future__ import annotations

import sys
import time
import zipfile
from pathlib import Path

from src.devtools.base_runtime_dependencies import copy_cpu_onnxruntime, gpu_extension_exclusions, without_onnxruntime_paths
from src.devtools.base_runtime_spec import (
    BASE_MANIFEST_NAME,
    BASE_MODEL_NAMES,
    BASE_PACKAGE_ID,
    BASE_PACKAGE_SCHEMA_VERSION,
    MANAGED_MODELS_NAME,
    STDLIB_ARCHIVE_NAME,
    base_model_names_for_variant,
)
from src.devtools.package_files import copy_file, copy_third_party_python_sources, copy_tree, print_elapsed, relative_files, write_json
from src.devtools.runtime_package_boundaries import is_excluded_relative_path
from src.services.runtime.release_manifest import MANIFEST_SCHEMA_VERSION, ReleaseManifestError
from src.services.runtime.variant import normalize_variant


def build_standard_library_archive(destination: Path) -> None:
    stdlib_root = Path(sys.prefix) / "Lib"
    if not stdlib_root.is_dir():
        raise ReleaseManifestError(f"Python 标准库目录不存在: {stdlib_root}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    skip_parts = {"test", "tests", "tkinter", "idlelib", "lib2to3", "site-packages"}
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source in sorted(stdlib_root.rglob("*.py")):
            relative = source.relative_to(stdlib_root)
            if any(part in skip_parts for part in relative.parts):
                continue
            archive.write(source, relative.as_posix())


def build_base_runtime_layer(app_root: Path, staging_root: Path, *, package_version: str, runtime_version: str, variant: str = "gpu", cpu_runtime_root: Path | None = None) -> Path:
    app_root = Path(app_root).resolve()
    staging_root = Path(staging_root).resolve()
    variant = normalize_variant(variant)
    runtime_root = app_root / "_internal"
    if not runtime_root.is_dir():
        raise ReleaseManifestError("PyInstaller 产物缺少 _internal 运行环境")
    if staging_root.exists():
        import shutil

        shutil.rmtree(staging_root)
    staging_root.mkdir(parents=True)
    extension_paths, extension_roots = gpu_extension_exclusions(variant)
    started = time.perf_counter()
    step = time.perf_counter()
    print("[Base] 正在复制冻结运行时文件...", flush=True)
    copy_tree(runtime_root, staging_root / "_internal", exclude_paths=extension_paths, exclude_roots=extension_roots)
    print_elapsed("[Base] 冻结运行时复制完成", step, perf_counter=time.perf_counter)
    if (runtime_root / "base_library.zip").is_file():
        step = time.perf_counter()
        print("[Base] 正在复制第三方 Python 源码...", flush=True)
        copy_third_party_python_sources(staging_root / "_internal", sys_prefix=Path(sys.prefix), exclude_paths=extension_paths, exclude_roots=extension_roots)
        print_elapsed("[Base] 第三方 Python 源码复制完成", step, perf_counter=time.perf_counter)
        step = time.perf_counter()
        print("[Base] 正在生成 Python 标准库压缩包...", flush=True)
        build_standard_library_archive(staging_root / "_internal" / STDLIB_ARCHIVE_NAME)
        print_elapsed("[Base] Python 标准库压缩包生成完成", step, perf_counter=time.perf_counter)
    if variant == "gpu" and cpu_runtime_root is not None:
        step = time.perf_counter()
        print("[Base] 正在覆盖 CPU ONNX Runtime...", flush=True)
        copy_cpu_onnxruntime(staging_root / "_internal", Path(cpu_runtime_root))
        print_elapsed("[Base] CPU ONNX Runtime 覆盖完成", step, perf_counter=time.perf_counter)
    model_source = app_root / "data" / "models"
    required_model = model_source / "yolo26n.pt"
    if not required_model.is_file():
        raise ReleaseManifestError("PyInstaller 产物缺少 data/models/yolo26n.pt")
    target_models = staging_root / "data" / "models"
    target_models.mkdir(parents=True, exist_ok=True)
    step = time.perf_counter()
    print("[Base] 正在复制基础模型...", flush=True)
    for model_name in base_model_names_for_variant(variant):
        model_path = model_source / model_name
        if not model_path.is_file():
            raise ReleaseManifestError(f"基础模型包缺少 data/models/{model_name}")
        copy_file(model_path, target_models / model_name)
    print_elapsed("[Base] 基础模型复制完成", step, perf_counter=time.perf_counter)
    step = time.perf_counter()
    print("[Base] 正在生成文件清单...", flush=True)
    runtime_files = relative_files(staging_root / "_internal")
    overlap_paths, overlap_roots = without_onnxruntime_paths(extension_paths, extension_roots)
    overlap = [relative for relative in runtime_files if is_excluded_relative_path(Path(relative), excluded_paths=overlap_paths, excluded_roots=overlap_roots)]
    if overlap:
        preview = ", ".join(overlap[:8])
        suffix = " ..." if len(overlap) > 8 else ""
        raise ReleaseManifestError(f"基础包仍包含附加环境文件：{preview}{suffix}")
    write_json(staging_root / "runtime-manifest.json", {"schema_version": MANIFEST_SCHEMA_VERSION, "runtime_version": runtime_version, "variant": variant})
    models_root = staging_root / "data" / "models"
    model_files = relative_files(models_root) if models_root.is_dir() else []
    write_json(staging_root / MANAGED_MODELS_NAME, {"schema_version": 1, "files": model_files})
    payload_files = [*(f"_internal/{relative}" for relative in runtime_files), *(f"data/models/{relative}" for relative in model_files), "runtime-manifest.json", MANAGED_MODELS_NAME]
    manifest = {"schema_version": BASE_PACKAGE_SCHEMA_VERSION, "package_id": BASE_PACKAGE_ID, "version": package_version, "runtime_version": runtime_version, "variant": variant, "platform": "win-64", "architecture": "x86_64", "uncompressed_size": sum((staging_root / Path(relative)).stat().st_size for relative in payload_files), "files": payload_files}
    manifest_path = staging_root / BASE_MANIFEST_NAME
    write_json(manifest_path, manifest)
    print_elapsed("[Base] 文件清单生成完成", step, perf_counter=time.perf_counter)
    print_elapsed("[Base] staging 构建完成", started, perf_counter=time.perf_counter)
    return manifest_path


__all__ = ["build_base_runtime_layer", "build_standard_library_archive"]
