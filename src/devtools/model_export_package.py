from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from importlib import metadata
from pathlib import Path, PurePosixPath

from src.devtools.runtime_package_boundaries import (
    GPU_EXTRA_DISTRIBUTIONS,
    distribution_relative_files,
    safe_distribution_path,
)

from src.services.model_export import (
    EXPORT_PROTOCOL_VERSION,
    EXTENSION_PACKAGE_ID,
    EXTENSION_SCHEMA_VERSION,
)
from src.services.model_export.manifest import ORT_GPU_OVERLAY_DIR, ORT_GPU_OVERLAY_KEY


OPTIONAL_DISTRIBUTIONS = GPU_EXTRA_DISTRIBUTIONS
EXTRA_ARCHIVE_VOLUME_BYTES = 1_073_700_000
EXTRA_ARCHIVE_VOLUME_COUNT = 2
MAX_ARCHIVE_VOLUME_BYTES = 1_073_741_824


def _relative_files(root: Path) -> list[str]:
    base = Path(root).resolve()
    return sorted(
        path.relative_to(base).as_posix()
        for path in base.rglob("*")
        if path.is_file()
    )


def _format_elapsed(seconds: float) -> str:
    if seconds >= 60:
        minutes, remainder = divmod(seconds, 60)
        return f"{int(minutes)} 分 {remainder:.2f} 秒"
    return f"{seconds:.2f} 秒"


def _print_elapsed(label: str, started: float) -> None:
    print(f"{label}，耗时：{_format_elapsed(time.perf_counter() - started)}", flush=True)


def _safe_distribution_path(value: object) -> Path | None:
    return safe_distribution_path(value)


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


def collect_runtime_overlays(package_root: Path) -> dict[str, str]:
    """Copy alternate runtimes under isolated roots without shadowing BaseEnv."""
    versions: dict[str, str] = {}
    try:
        distribution = metadata.distribution("onnxruntime-gpu")
    except metadata.PackageNotFoundError as exc:
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
    versions[ORT_GPU_OVERLAY_KEY] = distribution.version
    return versions


def _validate_no_base_overlap(
    staging_root: Path,
    base_staging_root: Path,
) -> None:
    manifest_path = Path(base_staging_root) / "base-package-manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError(f"基础包缺少清单，无法校验扩展边界：{manifest_path}")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    base_files = {
        PurePosixPath(str(value)).relative_to("_internal").as_posix()
        for value in payload.get("files", [])
        if PurePosixPath(str(value)).parts
        and PurePosixPath(str(value)).parts[0] == "_internal"
    }
    extension_files = {
        PurePosixPath(relative).as_posix()
        for relative in _relative_files(Path(staging_root) / "packages")
    }
    overlap = sorted(base_files & extension_files)
    if overlap:
        preview = ", ".join(overlap[:8])
        suffix = " ..." if len(overlap) > 8 else ""
        raise RuntimeError(f"基础包与附加包存在重复文件：{preview}{suffix}")


def _build_native_archive(
    staging_root: Path,
    archive_path: Path,
    *,
    split: bool = False,
) -> Path:
    seven_zip = shutil.which("7z") or shutil.which("7z.exe")
    if not seven_zip:
        raise RuntimeError("未找到 Pixi 提供的 7z 命令，无法构建模型转换附加包。")
    archive_started = time.perf_counter()
    print("[Extra] 正在使用 7-Zip 压缩，下面显示实时进度：", flush=True)
    archive_path.unlink(missing_ok=True)
    for volume_path in archive_path.parent.glob(f"{archive_path.name}.[0-9][0-9][0-9]"):
        volume_path.unlink(missing_ok=True)
    command = [
        seven_zip,
        "a",
        "-t7z",
        str(archive_path),
        "*",
    ]
    if split:
        command.append(f"-v{EXTRA_ARCHIVE_VOLUME_BYTES}b")
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
    completed = subprocess.run(
        command,
        cwd=staging_root,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"7z 模型转换附加包构建失败，退出码：{completed.returncode}"
        )
    if split:
        volume_paths = sorted(
            archive_path.parent.glob(f"{archive_path.name}.[0-9][0-9][0-9]")
        )
        if not volume_paths or len(volume_paths) > EXTRA_ARCHIVE_VOLUME_COUNT:
            raise RuntimeError(
                f"附加环境包最多允许生成 {EXTRA_ARCHIVE_VOLUME_COUNT} 个分卷，实际生成 {len(volume_paths)} 个。"
            )
        if any(path.stat().st_size >= MAX_ARCHIVE_VOLUME_BYTES for path in volume_paths):
            raise RuntimeError("附加环境包分卷必须严格小于 1 GiB。")
        first_volume_path = archive_path.with_name(f"{archive_path.name}.001")
        if not first_volume_path.is_file():
            raise RuntimeError("附加环境包分卷缺少首卷 .001。")
        _print_elapsed("[Extra] 7-Zip 分卷压缩完成", archive_started)
        for volume_path in volume_paths:
            print(
                f"[Extra] 分卷：{volume_path.name} ({volume_path.stat().st_size} bytes)",
                flush=True,
            )
        return first_volume_path
    if not archive_path.is_file():
        raise RuntimeError("附加环境包单卷归档未生成。")
    _print_elapsed("[Extra] 7-Zip 压缩完成", archive_started)
    print(f"[Extra] 单卷归档：{archive_path}", flush=True)
    return archive_path


def build_model_export_layer(
    staging_root: Path,
    *,
    version: str,
    base_staging_root: Path | None = None,
) -> Path:
    staging_root = Path(staging_root).resolve()
    if staging_root.exists():
        shutil.rmtree(staging_root)
    package_root = staging_root / "packages"
    package_root.mkdir(parents=True)
    step_started = time.perf_counter()
    versions = collect_optional_distributions(package_root)
    versions.update(collect_runtime_overlays(package_root))
    _print_elapsed("[Extra] 运行库文件复制完成", step_started)
    if base_staging_root is not None:
        _validate_no_base_overlap(staging_root, Path(base_staging_root).resolve())
    step_started = time.perf_counter()
    files = [f"packages/{relative}" for relative in _relative_files(package_root)]
    _print_elapsed("[Extra] 文件清单生成完成", step_started)
    dll_dirs = sorted(
        {
            str(Path(relative).parent).replace("\\", "/")
            for relative in files
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
        "supported_formats": ["openvino", "engine", "ncnn"],
        "dependencies": versions,
        "runtime_overlays": {ORT_GPU_OVERLAY_KEY: ORT_GPU_OVERLAY_DIR},
        "dll_dirs": dll_dirs,
        "files": files,
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
    base_staging_root: Path | None = None,
    split: bool = False,
) -> Path:
    staging_root = Path(staging_root).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / f"YOLOTool_ExtraEnv_{version}.7z"
    staging_started = time.perf_counter()
    print("[Extra] 正在准备模型转换运行库 staging...", flush=True)
    build_model_export_layer(
        staging_root,
        version=version,
        base_staging_root=base_staging_root,
    )
    _print_elapsed("[Extra] staging 构建完成", staging_started)
    return _build_native_archive(staging_root, archive_path, split=split)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build additive model export layer")
    parser.add_argument("--staging-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--base-staging", type=Path)
    parser.add_argument("--split", action="store_true")
    args = parser.parse_args()
    print(
        build_model_export_archive(
            args.staging_root,
            args.output_dir,
            version=args.version,
            base_staging_root=args.base_staging,
            split=args.split,
        )
    )


if __name__ == "__main__":
    main()
