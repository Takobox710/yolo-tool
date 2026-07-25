from __future__ import annotations

from pathlib import Path

from src.shared.paths import ROOT


METADATA_DIRECTORY_NAME = "yolotool_metadata"


def metadata_directory(root: str | Path = ROOT) -> Path:
    return Path(root) / "_internal" / METADATA_DIRECTORY_NAME


def metadata_path(root: str | Path, filename: str) -> Path:
    return metadata_directory(root) / filename


def resolve_metadata_path(root: str | Path, filename: str) -> Path:
    canonical = metadata_path(root, filename)
    if canonical.exists():
        return canonical
    legacy = Path(root) / filename
    return legacy if legacy.exists() else canonical
