from __future__ import annotations

import json
from pathlib import Path

from src.services.runtime.release_manifest import (
    ReleaseManifestError,
    validate_relative_path,
)
from src.services.runtime.metadata import resolve_metadata_path


MANAGED_MODELS_MANIFEST = "managed-models.json"


def remove_managed_models(install_root: str | Path) -> list[Path]:
    root = Path(install_root).resolve()
    models_root = (root / "data" / "models").resolve()
    manifest_path = resolve_metadata_path(root, MANAGED_MODELS_MANIFEST)
    if not manifest_path.is_file():
        return []

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseManifestError(f"无法读取受管模型清单: {exc}") from exc
    files = payload.get("files")
    if payload.get("schema_version") != 1 or not isinstance(files, (dict, list)):
        raise ReleaseManifestError("受管模型清单格式不受支持。")

    targets: list[Path] = []
    relative_files = files.keys() if isinstance(files, dict) else files
    for value in relative_files:
        relative = validate_relative_path(str(value))
        target = (models_root / Path(relative)).resolve()
        if not target.is_relative_to(models_root):
            raise ReleaseManifestError(f"受管模型路径超出模型目录: {value}")
        targets.append(target)

    removed: list[Path] = []
    for target in targets:
        if target.is_file() or target.is_symlink():
            target.unlink()
            removed.append(target)

    if models_root.is_dir():
        directories = sorted(
            (path for path in models_root.rglob("*") if path.is_dir()),
            key=lambda path: len(path.parts),
            reverse=True,
        )
        for directory in directories:
            try:
                directory.rmdir()
            except OSError:
                pass
    return removed
