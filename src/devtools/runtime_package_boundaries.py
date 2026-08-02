from __future__ import annotations

from importlib import metadata
from pathlib import Path, PurePosixPath


GPU_EXTRA_DISTRIBUTIONS = (
    "openvino",
    "openvino-telemetry",
    "nncf",
    "networkx",
    "scipy",
    "pandas",
    "ncnn",
    "pnnx",
    "tensorrt",
    "tensorrt-cu13",
    "tensorrt-cu13-libs",
    "tensorrt-cu13-bindings",
)


def safe_distribution_path(value: object) -> Path | None:
    path = PurePosixPath(str(value).replace("\\", "/"))
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        return None
    return Path(*path.parts)


def distribution_relative_files(distribution: metadata.Distribution) -> set[Path]:
    return {
        relative
        for item in distribution.files or ()
        if (relative := safe_distribution_path(item)) is not None
    }


def extension_distribution_paths(
    distributions: tuple[str, ...] = GPU_EXTRA_DISTRIBUTIONS,
) -> set[Path]:
    paths: set[Path] = set()
    for name in distributions:
        paths.update(distribution_relative_files(metadata.distribution(name)))
    return paths


def distribution_path_roots(paths: set[Path]) -> set[str]:
    return {path.parts[0] for path in paths if path.parts}


def is_excluded_relative_path(
    relative: Path,
    *,
    excluded_paths: set[Path] | frozenset[Path] = frozenset(),
    excluded_roots: set[str] | frozenset[str] = frozenset(),
) -> bool:
    normalized = Path(*PurePosixPath(relative.as_posix()).parts)
    return bool(
        normalized in excluded_paths
        or (normalized.parts and normalized.parts[0] in excluded_roots)
    )


__all__ = [
    "GPU_EXTRA_DISTRIBUTIONS",
    "distribution_path_roots",
    "distribution_relative_files",
    "extension_distribution_paths",
    "is_excluded_relative_path",
    "safe_distribution_path",
]
