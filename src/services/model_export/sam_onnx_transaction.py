from __future__ import annotations

import shutil
from pathlib import Path


def remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def cleanup_stale_sam2_export_workdirs(output_dir: str | Path) -> None:
    root = Path(output_dir)
    if not root.exists():
        return
    backup_prefix = ".sam2-export-backup-"
    for path in root.glob(".sam2-export-*"):
        if not path.name.startswith(backup_prefix):
            remove_path(path)
    for backup in root.glob(f"{backup_prefix}*"):
        remainder = backup.name[len(backup_prefix) :]
        _token, separator, target_name = remainder.partition("-")
        if not separator or not target_name:
            remove_path(backup)
            continue
        target = root / target_name
        if target.exists():
            remove_path(backup)
        else:
            backup.replace(target)


def promote_stage(stage: Path, target: Path, backup: Path) -> None:
    if target.exists():
        target.replace(backup)
    shutil.move(str(stage), str(target))


def rollback_target(target: Path, backup: Path) -> None:
    if backup.exists():
        remove_path(target)
        backup.replace(target)


__all__ = ["cleanup_stale_sam2_export_workdirs", "promote_stage", "remove_path", "rollback_target"]
