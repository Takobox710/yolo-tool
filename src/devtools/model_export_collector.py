from __future__ import annotations

import shutil
from importlib import metadata
from pathlib import Path

from src.devtools.runtime_package_boundaries import distribution_relative_files, safe_distribution_path
from src.services.model_export.manifest import ORT_GPU_OVERLAY_DIR, ORT_GPU_OVERLAY_KEY


def collect_optional_distributions(package_root: Path, distributions: tuple[str, ...], *, metadata_module=metadata) -> dict[str, str]:
    package_root = Path(package_root)
    versions: dict[str, str] = {}
    copied: set[Path] = set()
    for name in distributions:
        try:
            distribution = metadata_module.distribution(name)
        except metadata_module.PackageNotFoundError as exc:
            raise RuntimeError(f"模型转换环境缺少分发包：{name}") from exc
        versions[name] = distribution.version
        for relative in sorted(distribution_relative_files(distribution)):
            source = Path(distribution.locate_file(relative))
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


def collect_runtime_overlays(package_root: Path, *, metadata_module=metadata) -> dict[str, str]:
    try:
        distribution = metadata_module.distribution("onnxruntime-gpu")
    except metadata_module.PackageNotFoundError as exc:
        raise RuntimeError("模型转换环境缺少 GPU ONNX Runtime：onnxruntime-gpu") from exc
    target_root = Path(package_root) / ORT_GPU_OVERLAY_DIR
    copied = False
    for relative in sorted(distribution_relative_files(distribution)):
        source = Path(distribution.locate_file(relative))
        if not source.is_file():
            continue
        target = target_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied = True
    if not copied:
        raise RuntimeError("未收集到 GPU ONNX Runtime 文件。")
    return {ORT_GPU_OVERLAY_KEY: distribution.version}


__all__ = ["collect_optional_distributions", "collect_runtime_overlays", "safe_distribution_path"]
