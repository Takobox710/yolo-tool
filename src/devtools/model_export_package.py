from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from importlib import metadata
from pathlib import Path, PurePosixPath

from src.services.model_export import (
    EXPORT_PROTOCOL_VERSION,
    EXTENSION_PACKAGE_ID,
    EXTENSION_SCHEMA_VERSION,
)


OPTIONAL_DISTRIBUTIONS = (
    "openvino",
    "openvino-telemetry",
    "ncnn",
    "pnnx",
    "tensorrt",
    "tensorrt-cu13",
    "tensorrt-cu13-libs",
    "tensorrt-cu13-bindings",
)


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
    path = PurePosixPath(str(value).replace("\\", "/"))
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        return None
    return Path(*path.parts)


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
        for item in distribution.files or ():
            relative = _safe_distribution_path(item)
            if relative is None:
                continue
            source = Path(distribution.locate_file(item))
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


def _build_native_archive(staging_root: Path, archive_path: Path) -> None:
    seven_zip = shutil.which("7z") or shutil.which("7z.exe")
    if not seven_zip:
        raise RuntimeError("未找到 Pixi 提供的 7z 命令，无法构建模型转换附加包。")
    archive_started = time.perf_counter()
    print("[Extra] 正在使用 7-Zip 压缩，下面显示实时进度：", flush=True)
    completed = subprocess.run(
        [
            seven_zip,
            "a",
            "-t7z",
            str(archive_path),
            "*",
            "-m0=lzma2",
            "-mx=5",
            "-ms=off",
            "-mmt=on",
            "-bsp1",
            "-bb0",
        ],
        cwd=staging_root,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"7z 模型转换附加包构建失败，退出码：{completed.returncode}"
        )
    _print_elapsed("[Extra] 7-Zip 压缩完成", archive_started)
    print(f"[Extra] 归档路径：{archive_path}", flush=True)


def build_model_export_layer(staging_root: Path, *, version: str) -> Path:
    staging_root = Path(staging_root).resolve()
    if staging_root.exists():
        shutil.rmtree(staging_root)
    package_root = staging_root / "packages"
    package_root.mkdir(parents=True)
    step_started = time.perf_counter()
    versions = collect_optional_distributions(package_root)
    _print_elapsed("[Extra] 运行库文件复制完成", step_started)
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
) -> Path:
    staging_root = Path(staging_root).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / f"YOLOTool_ExtraEnv_{version}.7z"
    staging_started = time.perf_counter()
    print("[Extra] 正在准备模型转换运行库 staging...", flush=True)
    build_model_export_layer(staging_root, version=version)
    _print_elapsed("[Extra] staging 构建完成", staging_started)
    archive_path.unlink(missing_ok=True)
    _build_native_archive(staging_root, archive_path)
    return archive_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build additive model export layer")
    parser.add_argument("--staging-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    print(
        build_model_export_archive(
            args.staging_root,
            args.output_dir,
            version=args.version,
        )
    )


if __name__ == "__main__":
    main()
