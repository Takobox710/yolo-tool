from __future__ import annotations

import configparser
import json
import os
import shutil
import subprocess
from pathlib import Path

from src.services.runtime.release_manifest import ReleaseManifestError
from src.devtools.runtime_package_boundaries import is_excluded_relative_path


THIRD_PARTY_SOURCE_EXCLUDE_ROOTS = frozenset(
    {
        "_distutils_hack", "_polars_runtime_32", "_pytest",
        "_pyinstaller_hooks_contrib", "PyInstaller", "adodbapi",
        "altgraph", "iniconfig", "isapi", "pluggy", "polars",
        "pydevd_plugins", "pytest", "pythonwin", "setuptools",
        "torchaudio", "win32", "win32com", "win32comext",
    }
)
THIRD_PARTY_SOURCE_EXCLUDE_PARTS = frozenset(
    {"SelfTest", "_examples", "example", "examples", "test", "testdata", "testing", "tests"}
)


def format_elapsed(seconds: float) -> str:
    if seconds >= 60:
        minutes, remainder = divmod(seconds, 60)
        return f"{int(minutes)} 分 {remainder:.2f} 秒"
    return f"{seconds:.2f} 秒"


def print_elapsed(label: str, started: float, *, perf_counter) -> None:
    print(f"{label}，耗时：{format_elapsed(perf_counter() - started)}", flush=True)


def should_skip_third_party_source(relative: Path) -> bool:
    parts = relative.parts
    return bool(
        parts
        and (
            parts[0] in THIRD_PARTY_SOURCE_EXCLUDE_ROOTS
            or any(part in THIRD_PARTY_SOURCE_EXCLUDE_PARTS for part in parts)
        )
    )


def copy_file(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise ReleaseManifestError(f"打包源文件不存在: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def copy_tree(
    source: Path,
    destination: Path,
    *,
    exclude_paths: set[Path] | frozenset[Path] = frozenset(),
    exclude_roots: set[str] | frozenset[str] = frozenset(),
) -> None:
    if not source.is_dir():
        raise ReleaseManifestError(f"打包源目录不存在: {source}")
    if not exclude_paths and not exclude_roots:
        shutil.copytree(source, destination, dirs_exist_ok=True)
        return
    for item in sorted(source.rglob("*")):
        if not item.is_file():
            continue
        relative = item.relative_to(source)
        if is_excluded_relative_path(
            relative,
            excluded_paths=exclude_paths,
            excluded_roots=exclude_roots,
        ):
            continue
        copy_file(item, destination / relative)


def relative_files(root: Path) -> list[str]:
    base = Path(root).resolve()
    return sorted(
        path.relative_to(base).as_posix()
        for path in base.rglob("*")
        if path.is_file()
    )


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_package_info(
    path: Path,
    *,
    package_type: str,
    app_version: str,
    required_runtime_version: str,
    variant: str = "gpu",
) -> None:
    config = configparser.ConfigParser()
    config["Package"] = {
        "type": package_type,
        "app_version": app_version,
        "required_runtime_version": required_runtime_version,
        "variant": variant,
    }
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        config.write(handle)


def copy_third_party_python_sources(
    runtime_root: Path,
    *,
    sys_prefix: Path,
    exclude_paths: set[Path] | frozenset[Path] = frozenset(),
    exclude_roots: set[str] | frozenset[str] = frozenset(),
) -> None:
    """Restore pure package files that PyInstaller normally embeds in PYZ."""
    site_packages = Path(sys_prefix) / "Lib" / "site-packages"
    if not site_packages.is_dir():
        raise ReleaseManifestError(f"第三方包目录不存在: {site_packages}")
    skip_parts = THIRD_PARTY_SOURCE_EXCLUDE_PARTS | {"__pycache__"}
    robocopy = shutil.which("robocopy") if os.name == "nt" else None
    if robocopy and not exclude_paths and not exclude_roots:
        completed = subprocess.run(
            [
                robocopy, str(site_packages), str(runtime_root), "*.py", "/S",
                "/MT:16", "/R:0", "/W:0", "/COPY:DAT", "/DCOPY:DAT", "/XJ",
                "/NFL", "/NDL", "/NJH", "/NJS", "/NP", "/XD",
                *sorted(THIRD_PARTY_SOURCE_EXCLUDE_ROOTS | skip_parts),
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if completed.returncode > 7:
            raise ReleaseManifestError(
                f"robocopy 复制第三方 Python 源码失败，退出码: {completed.returncode}"
            )
        return
    for source in sorted(site_packages.rglob("*.py")):
        relative = source.relative_to(site_packages)
        if should_skip_third_party_source(relative):
            continue
        if is_excluded_relative_path(
            relative,
            excluded_paths=exclude_paths,
            excluded_roots=exclude_roots,
        ):
            continue
        destination = runtime_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


__all__ = [
    "THIRD_PARTY_SOURCE_EXCLUDE_PARTS",
    "THIRD_PARTY_SOURCE_EXCLUDE_ROOTS",
    "copy_file",
    "copy_third_party_python_sources",
    "copy_tree",
    "format_elapsed",
    "print_elapsed",
    "relative_files",
    "should_skip_third_party_source",
    "write_json",
    "write_package_info",
]
