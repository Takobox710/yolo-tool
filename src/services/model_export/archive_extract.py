from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path
from typing import Callable

import py7zr

from src.services.model_export.native_archive import NativeArchiveError, extract_archive


class ArchiveExtractionError(ValueError):
    """Raised when an archive cannot be extracted."""


def extract_zip(archive_path: Path, destination: Path, manifest: dict) -> dict:
    expected = set(manifest["files"])
    with zipfile.ZipFile(archive_path) as archive:
        for info in archive.infolist():
            relative = info.filename.replace("\\", "/").rstrip("/")
            if info.is_dir() or relative not in expected:
                continue
            target = destination / Path(relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
    (destination / "extension-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


def extract_7z(
    archive_path: Path,
    destination: Path,
    manifest: dict,
    *,
    progress: Callable[[int], None] | None = None,
) -> dict:
    try:
        extract_archive(archive_path, destination, progress=progress)
        return manifest
    except NativeArchiveError:
        pass
    targets = ["extension-manifest.json", *manifest["files"]]
    try:
        with py7zr.SevenZipFile(archive_path, "r") as archive:
            archive.extract(path=destination, targets=targets)
    except (OSError, py7zr.Bad7zFile) as exc:
        raise ArchiveExtractionError("无法解压 7z 模型转换环境包。") from exc
    return manifest
