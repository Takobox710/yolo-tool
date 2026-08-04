from __future__ import annotations

import shutil
from importlib import metadata
from pathlib import Path

from src.devtools.package_files import copy_tree
from src.devtools.runtime_package_boundaries import (
    GPU_BASE_EXCLUDED_DISTRIBUTIONS,
    distribution_path_roots,
    extension_distribution_paths,
)
from src.services.runtime.release_manifest import ReleaseManifestError


def gpu_extension_exclusions(variant: str) -> tuple[set[Path], set[str]]:
    if variant != "gpu":
        return set(), set()
    try:
        paths = extension_distribution_paths(GPU_BASE_EXCLUDED_DISTRIBUTIONS)
    except metadata.PackageNotFoundError as exc:
        raise ReleaseManifestError(f"GPU 打包环境缺少模型转换分发包：{exc.name}") from exc
    return paths, distribution_path_roots(paths)


def copy_cpu_onnxruntime(staging_internal: Path, cpu_runtime_root: Path) -> None:
    site_packages = Path(cpu_runtime_root).resolve() / "Lib" / "site-packages"
    package_source = site_packages / "onnxruntime"
    if not package_source.is_dir():
        raise ReleaseManifestError(f"CPU ONNX Runtime 目录不存在：{package_source}")
    dist_infos = sorted(site_packages.glob("onnxruntime-*.dist-info"))
    if not dist_infos:
        raise ReleaseManifestError(f"CPU ONNX Runtime 缺少 dist-info：{site_packages}")
    try:
        gpu_version = metadata.version("onnxruntime-gpu")
    except metadata.PackageNotFoundError as exc:
        raise ReleaseManifestError("GPU 打包环境缺少 onnxruntime-gpu。") from exc
    cpu_version = dist_infos[0].name[len("onnxruntime-") : -len(".dist-info")]
    if cpu_version != gpu_version:
        raise ReleaseManifestError(f"CPU/GPU ONNX Runtime 版本不一致：CPU {cpu_version}，GPU {gpu_version}")
    target_package = staging_internal / "onnxruntime"
    if target_package.exists():
        shutil.rmtree(target_package)
    for candidate in staging_internal.glob("onnxruntime*.dist-info"):
        if candidate.is_dir():
            shutil.rmtree(candidate)
    copy_tree(package_source, target_package)
    for dist_info in dist_infos:
        copy_tree(dist_info, staging_internal / dist_info.name)


def without_onnxruntime_paths(paths: set[Path], roots: set[str]) -> tuple[set[Path], set[str]]:
    return ({path for path in paths if not path.parts[0].startswith("onnxruntime")}, {root for root in roots if not root.startswith("onnxruntime")})


__all__ = ["copy_cpu_onnxruntime", "gpu_extension_exclusions", "without_onnxruntime_paths"]
