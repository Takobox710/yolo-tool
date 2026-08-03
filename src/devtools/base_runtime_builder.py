from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from importlib import metadata
from pathlib import Path

from src.services.runtime.release_manifest import MANIFEST_SCHEMA_VERSION, ReleaseManifestError
from src.services.runtime.variant import normalize_variant, variant_asset_prefix
from src.devtools.package_files import (
    copy_file,
    copy_third_party_python_sources,
    copy_tree,
    print_elapsed,
    relative_files,
    write_json,
)
from src.devtools.runtime_package_boundaries import (
    GPU_BASE_EXCLUDED_DISTRIBUTIONS,
    distribution_path_roots,
    extension_distribution_paths,
    is_excluded_relative_path,
)


BASE_PACKAGE_SCHEMA_VERSION = 1
BASE_PACKAGE_ID = "yolo-tool-base-runtime-models"
BASE_MANIFEST_NAME = "base-package-manifest.json"
MANAGED_MODELS_NAME = "managed-models.json"
GPU_BASE_MODEL_NAMES = (
    "yolo11s.pt",
    "yolo26n.pt",
    "yolov8n.pt",
    "sam2.1_hiera_base_plus.pt",
)
CPU_BASE_MODEL_NAMES = (
    "yolo11s.pt",
    "yolo26n.pt",
    "yolov8n.pt",
    "sam2.1_hiera_tiny.pt",
)
# Keep the historical export pointing at the GPU release list.
BASE_MODEL_NAMES = GPU_BASE_MODEL_NAMES
STDLIB_ARCHIVE_NAME = "python_stdlib.zip"
BASE_ARCHIVE_VOLUME_BYTES = 1_073_700_000
BASE_ARCHIVE_VOLUME_COUNT = 2


def base_model_names_for_variant(variant: str) -> tuple[str, ...]:
    return CPU_BASE_MODEL_NAMES if normalize_variant(variant) == "cpu" else GPU_BASE_MODEL_NAMES


def _gpu_extension_exclusions(variant: str) -> tuple[set[Path], set[str]]:
    if variant != "gpu":
        return set(), set()
    try:
        paths = extension_distribution_paths(GPU_BASE_EXCLUDED_DISTRIBUTIONS)
    except metadata.PackageNotFoundError as exc:
        raise ReleaseManifestError(
            f"GPU 打包环境缺少模型转换分发包：{exc.name}"
        ) from exc
    return paths, distribution_path_roots(paths)


def _copy_cpu_onnxruntime(
    staging_internal: Path,
    cpu_runtime_root: Path,
) -> None:
    site_packages = Path(cpu_runtime_root).resolve() / "Lib" / "site-packages"
    package_source = site_packages / "onnxruntime"
    if not package_source.is_dir():
        raise ReleaseManifestError(
            f"CPU ONNX Runtime 目录不存在：{package_source}"
        )
    dist_infos = sorted(site_packages.glob("onnxruntime-*.dist-info"))
    if not dist_infos:
        raise ReleaseManifestError(
            f"CPU ONNX Runtime 缺少 dist-info：{site_packages}"
        )
    try:
        gpu_version = metadata.version("onnxruntime-gpu")
    except metadata.PackageNotFoundError as exc:
        raise ReleaseManifestError("GPU 打包环境缺少 onnxruntime-gpu。") from exc
    cpu_version = dist_infos[0].name[len("onnxruntime-") : -len(".dist-info")]
    if cpu_version != gpu_version:
        raise ReleaseManifestError(
            f"CPU/GPU ONNX Runtime 版本不一致：CPU {cpu_version}，GPU {gpu_version}"
        )

    target_package = staging_internal / "onnxruntime"
    if target_package.exists():
        shutil.rmtree(target_package)
    for candidate in staging_internal.glob("onnxruntime*.dist-info"):
        if candidate.is_dir():
            shutil.rmtree(candidate)
    copy_tree(package_source, target_package)
    for dist_info in dist_infos:
        copy_tree(dist_info, staging_internal / dist_info.name)


def _without_onnxruntime_paths(
    paths: set[Path],
    roots: set[str],
) -> tuple[set[Path], set[str]]:
    return (
        {path for path in paths if not path.parts[0].startswith("onnxruntime")},
        {root for root in roots if not root.startswith("onnxruntime")},
    )


def build_standard_library_archive(destination: Path) -> None:
    """Add source modules dynamically imported by external frozen packages."""
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


def build_base_runtime_layer(
    app_root: Path,
    staging_root: Path,
    *,
    package_version: str,
    runtime_version: str,
    variant: str = "gpu",
    cpu_runtime_root: Path | None = None,
) -> Path:
    app_root = Path(app_root).resolve()
    staging_root = Path(staging_root).resolve()
    variant = normalize_variant(variant)
    runtime_root = app_root / "_internal"
    if not runtime_root.is_dir():
        raise ReleaseManifestError("PyInstaller 产物缺少 _internal 运行环境")
    if staging_root.exists():
        shutil.rmtree(staging_root)
    staging_root.mkdir(parents=True)
    extension_paths, extension_roots = _gpu_extension_exclusions(variant)

    staging_started = time.perf_counter()
    step_started = time.perf_counter()
    print("[Base] 正在复制冻结运行时文件...", flush=True)
    copy_tree(
        runtime_root,
        staging_root / "_internal",
        exclude_paths=extension_paths,
        exclude_roots=extension_roots,
    )
    print_elapsed("[Base] 冻结运行时复制完成", step_started, perf_counter=time.perf_counter)
    if (runtime_root / "base_library.zip").is_file():
        step_started = time.perf_counter()
        print("[Base] 正在复制第三方 Python 源码...", flush=True)
        copy_third_party_python_sources(
            staging_root / "_internal",
            sys_prefix=Path(sys.prefix),
            exclude_paths=extension_paths,
            exclude_roots=extension_roots,
        )
        print_elapsed("[Base] 第三方 Python 源码复制完成", step_started, perf_counter=time.perf_counter)
        step_started = time.perf_counter()
        print("[Base] 正在生成 Python 标准库压缩包...", flush=True)
        build_standard_library_archive(staging_root / "_internal" / STDLIB_ARCHIVE_NAME)
        print_elapsed("[Base] Python 标准库压缩包生成完成", step_started, perf_counter=time.perf_counter)
    if variant == "gpu" and cpu_runtime_root is not None:
        step_started = time.perf_counter()
        print("[Base] 正在覆盖 CPU ONNX Runtime...", flush=True)
        _copy_cpu_onnxruntime(staging_root / "_internal", Path(cpu_runtime_root))
        print_elapsed("[Base] CPU ONNX Runtime 覆盖完成", step_started, perf_counter=time.perf_counter)

    model_source = app_root / "data" / "models"
    required_model = model_source / "yolo26n.pt"
    if not required_model.is_file():
        raise ReleaseManifestError("PyInstaller 产物缺少 data/models/yolo26n.pt")
    target_models = staging_root / "data" / "models"
    target_models.mkdir(parents=True, exist_ok=True)
    step_started = time.perf_counter()
    print("[Base] 正在复制基础模型...", flush=True)
    for model_name in base_model_names_for_variant(variant):
        model_path = model_source / model_name
        if not model_path.is_file():
            raise ReleaseManifestError(f"基础模型包缺少 data/models/{model_name}")
        copy_file(model_path, target_models / model_name)
    print_elapsed("[Base] 基础模型复制完成", step_started, perf_counter=time.perf_counter)

    step_started = time.perf_counter()
    print("[Base] 正在生成文件清单...", flush=True)
    runtime_files = relative_files(staging_root / "_internal")
    overlap_paths, overlap_roots = _without_onnxruntime_paths(
        extension_paths,
        extension_roots,
    )
    overlap = [
        relative
        for relative in runtime_files
        if is_excluded_relative_path(
            Path(relative),
            excluded_paths=overlap_paths,
            excluded_roots=overlap_roots,
        )
    ]
    if overlap:
        preview = ", ".join(overlap[:8])
        suffix = " ..." if len(overlap) > 8 else ""
        raise ReleaseManifestError(f"基础包仍包含附加环境文件：{preview}{suffix}")
    write_json(
        staging_root / "runtime-manifest.json",
        {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "runtime_version": runtime_version,
            "variant": variant,
        },
    )
    models_root = staging_root / "data" / "models"
    model_files = relative_files(models_root) if models_root.is_dir() else []
    write_json(staging_root / MANAGED_MODELS_NAME, {"schema_version": 1, "files": model_files})
    payload_files = [
        *(f"_internal/{relative}" for relative in runtime_files),
        *(f"data/models/{relative}" for relative in model_files),
        "runtime-manifest.json",
        MANAGED_MODELS_NAME,
    ]
    unpacked_size = sum((staging_root / Path(relative)).stat().st_size for relative in payload_files)
    manifest = {
        "schema_version": BASE_PACKAGE_SCHEMA_VERSION,
        "package_id": BASE_PACKAGE_ID,
        "version": package_version,
        "runtime_version": runtime_version,
        "variant": variant,
        "platform": "win-64",
        "architecture": "x86_64",
        "uncompressed_size": unpacked_size,
        "files": payload_files,
    }
    manifest_path = staging_root / BASE_MANIFEST_NAME
    write_json(manifest_path, manifest)
    print_elapsed("[Base] 文件清单生成完成", step_started, perf_counter=time.perf_counter)
    print_elapsed("[Base] staging 构建完成", staging_started, perf_counter=time.perf_counter)
    return manifest_path


def build_base_runtime_archive(
    app_root: Path,
    staging_root: Path,
    output_dir: Path,
    *,
    package_version: str,
    runtime_version: str,
    variant: str = "gpu",
    split: bool = False,
    cpu_runtime_root: Path | None = None,
) -> Path:
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    variant = normalize_variant(variant)
    archive_path = output_dir / (
        f"{variant_asset_prefix(variant)}_BaseEnv_{package_version}.7z"
    )
    first_volume_path = Path(f"{archive_path}.001")
    build_base_runtime_layer(
        app_root,
        staging_root,
        package_version=package_version,
        runtime_version=runtime_version,
        variant=variant,
        cpu_runtime_root=cpu_runtime_root,
    )
    if split:
        for volume_path in output_dir.glob(f"{archive_path.name}.[0-9][0-9][0-9]"):
            volume_path.unlink(missing_ok=True)
    else:
        archive_path.unlink(missing_ok=True)
    seven_zip = shutil.which("7z") or shutil.which("7z.exe")
    if not seven_zip:
        raise ReleaseManifestError("未找到 Pixi 提供的 7z 命令，无法构建基础环境包。")
    split_temp_dir = (
        tempfile.TemporaryDirectory(
            dir=output_dir,
            prefix=f".{archive_path.stem}.split-",
        )
        if split
        else None
    )
    archive_command_path = (
        Path(split_temp_dir.name) / archive_path.name
        if split_temp_dir is not None
        else archive_path
    )
    archive_started = time.perf_counter()
    print("[Base] 正在使用 7-Zip 压缩，下面显示实时进度：", flush=True)
    command = [
        seven_zip,
        "a",
        "-t7z",
        str(archive_command_path),
        "*",
    ]
    if split:
        command.append(f"-v{BASE_ARCHIVE_VOLUME_BYTES}b")
    command.extend(
        [
            "-m0=lzma2",
            "-mx=5",
            "-ms=off",
            "-mmt=on",
            "-bsp1",
            "-bb0",
        ]
    )
    try:
        completed = subprocess.run(
            command,
            cwd=Path(staging_root).resolve(),
            check=False,
        )
        if completed.returncode != 0:
            raise ReleaseManifestError(f"7z 基础环境包构建失败，退出码：{completed.returncode}")
        if split:
            volume_paths = sorted(
                archive_command_path.parent.glob(
                    f"{archive_command_path.name}.[0-9][0-9][0-9]"
                )
            )
            if not volume_paths or len(volume_paths) > BASE_ARCHIVE_VOLUME_COUNT:
                raise ReleaseManifestError(
                    f"基础环境包最多允许生成 {BASE_ARCHIVE_VOLUME_COUNT} 个分卷，实际生成 {len(volume_paths)} 个。"
                )
            if any(path.stat().st_size >= 1_073_741_824 for path in volume_paths):
                raise ReleaseManifestError("基础环境包分卷必须严格小于 1 GiB。")
            for volume_path in volume_paths:
                volume_path.replace(output_dir / volume_path.name)
        elif not archive_path.is_file():
            raise ReleaseManifestError("基础环境包单卷归档未生成。")
        print_elapsed("[Base] 7-Zip 压缩完成", archive_started, perf_counter=time.perf_counter)
        if split:
            print(f"[Base] 归档首卷：{first_volume_path}", flush=True)
            final_volume_paths = sorted(
                output_dir.glob(f"{archive_path.name}.[0-9][0-9][0-9]")
            )
            for volume_path in final_volume_paths:
                print(f"[Base] 分卷：{volume_path.name} ({volume_path.stat().st_size} bytes)", flush=True)
            return first_volume_path
        print(f"[Base] 单卷归档：{archive_path}", flush=True)
        return archive_path
    finally:
        if split_temp_dir is not None:
            split_temp_dir.cleanup()


__all__ = [
    "BASE_MANIFEST_NAME",
    "BASE_MODEL_NAMES",
    "CPU_BASE_MODEL_NAMES",
    "GPU_BASE_MODEL_NAMES",
    "BASE_PACKAGE_ID",
    "BASE_PACKAGE_SCHEMA_VERSION",
    "BASE_ARCHIVE_VOLUME_BYTES",
    "BASE_ARCHIVE_VOLUME_COUNT",
    "MANAGED_MODELS_NAME",
    "STDLIB_ARCHIVE_NAME",
    "build_base_runtime_archive",
    "build_base_runtime_layer",
    "build_standard_library_archive",
    "base_model_names_for_variant",
]
