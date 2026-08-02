"""Validate that a CPU build does not contain GPU inference runtimes."""

from __future__ import annotations

import argparse
from importlib import metadata
from pathlib import Path


FORBIDDEN_DISTRIBUTION_PREFIXES = (
    "onnxruntime-gpu",
    "tensorrt",
    "tensorrt-",
    "nvidia-cuda",
    "nvidia-cublas",
    "nvidia-cudnn",
    "nvidia-cuda-runtime",
    "nvidia-cuda-cupti",
    "nvidia-cusolver",
    "nvidia-cusparse",
    "nvidia-nccl",
    "nvidia-nvjitlink",
    "nvidia-nvtx",
)
FORBIDDEN_FILE_TOKENS = (
    "cudart",
    "cublas",
    "cudnn",
    "nvinfer",
    "nvonnxparser",
    "tensorrt",
    "onnxruntime_providers_cuda",
    "onnxruntime_providers_tensorrt",
    "openvino_auto_batch_plugin",
    "openvino_auto_plugin",
    "openvino_hetero_plugin",
    "openvino_intel_gpu_plugin",
    "openvino_intel_npu_",
)
FORBIDDEN_FROZEN_PACKAGE_PARTS = (
    "onnxruntime-gpu",
    "onnxruntime_gpu",
    "tensorrt",
    "tensorrt-cu13",
    "tensorrt_cu13",
    "nvidia-cuda",
    "nvidia_cuda",
    "nvidia-cublas",
    "nvidia_cublas",
    "nvidia-cudnn",
    "nvidia_cudnn",
)
FORBIDDEN_NATIVE_RELATIVE_PATHS = {"sam2/_c.pyd"}
REQUIRED_CPU_LOCK_TOKENS = (
    "/whl/cpu/torch-",
    "/whl/cpu/torchvision-",
    "/whl/cpu/torchaudio-",
    "onnxruntime-",
)
FORBIDDEN_LOCK_TOKENS = (
    "onnxruntime-gpu",
    "tensorrt",
    "nvidia-cuda",
    "nvidia-cublas",
    "nvidia-cudnn",
    "nvidia-cusolver",
    "nvidia-cusparse",
    "nvidia-nccl",
    "nvidia-nvjitlink",
    "nvidia-nvtx",
    "cudart",
    "cublas",
    "cudnn",
    "nvinfer",
    "nvonnxparser",
    "onnxruntime_providers_cuda",
    "onnxruntime_providers_tensorrt",
)


def validate_cpu_environment() -> list[str]:
    errors: list[str] = []
    distributions = {
        str(dist.metadata.get("Name") or dist.name).casefold()
        for dist in metadata.distributions()
    }
    for name in sorted(distributions):
        if any(name == prefix or name.startswith(prefix) for prefix in FORBIDDEN_DISTRIBUTION_PREFIXES):
            errors.append(f"CPU 环境包含禁止的分发包：{name}")
    try:
        torch_version = metadata.version("torch")
    except metadata.PackageNotFoundError:
        errors.append("CPU 环境缺少 torch。")
    else:
        if "+cu" in torch_version.casefold() or "+cuda" in torch_version.casefold():
            errors.append(f"CPU 环境使用了 CUDA Torch：{torch_version}")
    try:
        metadata.version("onnxruntime")
    except metadata.PackageNotFoundError:
        errors.append("CPU 环境缺少 CPU onnxruntime。")
    return errors


def validate_frozen_runtime(root: str | Path) -> list[str]:
    runtime_root = Path(root).resolve()
    if not runtime_root.is_dir():
        return [f"冻结运行时目录不存在：{runtime_root}"]
    errors: list[str] = []
    for path in runtime_root.rglob("*"):
        if not path.is_file():
            continue
        lowered = str(path).casefold().replace("\\", "/")
        relative = path.relative_to(runtime_root).as_posix().casefold()
        package_parts = {part.casefold() for part in path.relative_to(runtime_root).parts}
        if package_parts.intersection(FORBIDDEN_FROZEN_PACKAGE_PARTS):
            errors.append(f"冻结运行时包含禁止包路径：{path.relative_to(runtime_root)}")
            continue
        if relative in FORBIDDEN_NATIVE_RELATIVE_PATHS:
            errors.append(f"冻结运行时包含禁止 CUDA 扩展：{path.relative_to(runtime_root)}")
            continue
        if path.suffix.casefold() not in {".dll", ".pyd", ".so", ".dylib", ".exe"}:
            continue
        for token in FORBIDDEN_FILE_TOKENS:
            if token in lowered:
                errors.append(f"冻结运行时包含禁止文件：{path.relative_to(runtime_root)}")
                break
    return errors


def validate_cpu_lock(lock_path: str | Path) -> list[str]:
    """Check the packages selected for the release-cpu lock environment."""
    path = Path(lock_path)
    try:
        import yaml

        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        return [f"无法读取 CPU 锁文件：{path} ({exc})"]
    except ImportError as exc:
        return [f"CPU 锁文件检查缺少 PyYAML：{exc}"]

    if not isinstance(payload, dict):
        return [f"CPU 锁文件格式无效：{path}"]
    environment = payload.get("environments", {}).get("release-cpu", {})
    package_groups = environment.get("packages", {}) if isinstance(environment, dict) else {}
    entries: list[str] = []
    if isinstance(package_groups, dict):
        for group in package_groups.values():
            if not isinstance(group, list):
                continue
            for item in group:
                if isinstance(item, dict):
                    entries.extend(str(value).casefold() for value in item.values())
    if not entries:
        return ["CPU 锁文件缺少 environments.release-cpu.packages。"]

    errors: list[str] = []
    for token in FORBIDDEN_LOCK_TOKENS:
        if any(token in entry for entry in entries):
            errors.append(f"CPU 锁环境包含禁止内容：{token}")
    for token in REQUIRED_CPU_LOCK_TOKENS:
        if not any(token in entry for entry in entries):
            errors.append(f"CPU 锁环境缺少必需内容：{token}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate CPU package contents")
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument(
        "--lock-file",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "pixi.lock",
    )
    args = parser.parse_args()
    errors = validate_cpu_environment()
    errors.extend(validate_cpu_lock(args.lock_file))
    if args.runtime_root is not None:
        errors.extend(validate_frozen_runtime(args.runtime_root))
    if errors:
        for error in errors:
            print(error)
        return 1
    print("CPU package guard passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
