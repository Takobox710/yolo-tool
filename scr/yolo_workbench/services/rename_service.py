from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp"}


@dataclass
class RenamePlanItem:
    source: Path
    target: Path
    index: int
    old_name: str
    new_name: str
    conflict: bool
    label_source: Path | None = None
    label_target: Path | None = None
    label_conflict: bool = False
    note: str = ""


@dataclass
class RenameResult:
    renamed_count: int
    skipped_count: int
    label_renamed_count: int = 0


def preview_rename(folder: Path, prefix: str, start: int, padding: int, labels_dir: Path | None = None, include_labels: bool = False) -> list[RenamePlanItem]:
    files = sorted(path for path in Path(folder).iterdir() if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES)
    plan: list[RenamePlanItem] = []
    for offset, source in enumerate(files):
        number = start + offset
        new_name = f"{prefix}{number:0{padding}d}{source.suffix.lower()}"
        target = source.with_name(new_name)
        conflict = target.exists() and target.resolve() != source.resolve()
        label_source = None
        label_target = None
        label_conflict = False
        note = ""
        if include_labels and labels_dir is not None:
            label_source = Path(labels_dir) / f"{source.stem}.txt"
            label_target = Path(labels_dir) / f"{Path(new_name).stem}.txt"
            if not label_source.exists():
                note = "未找到同名标注"
                label_source = None
                label_target = None
            elif label_target.exists() and label_target.resolve() != label_source.resolve():
                label_conflict = True
                note = f"标注目标已存在: {label_target.name}"
        plan.append(
            RenamePlanItem(
                source=source,
                target=target,
                index=offset + 1,
                old_name=source.name,
                new_name=new_name,
                conflict=conflict,
                label_source=label_source,
                label_target=label_target,
                label_conflict=label_conflict,
                note=note,
            )
        )
    return plan


def execute_rename(plan: list[RenamePlanItem]) -> RenameResult:
    renamed = 0
    skipped = 0
    label_renamed = 0
    if any(item.label_conflict for item in plan):
        return RenameResult(renamed_count=0, skipped_count=len(plan))
    image_temp_paths: list[tuple[Path, Path]] = []
    label_temp_paths: list[tuple[Path, Path]] = []
    for item in plan:
        temp = item.source.with_name(f".__rename_tmp_{item.index}_{item.source.name}")
        item.source.rename(temp)
        image_temp_paths.append((temp, item.target))
        if item.label_source and item.label_target:
            label_temp = item.label_source.with_name(f".__rename_tmp_{item.index}_{item.label_source.name}")
            item.label_source.rename(label_temp)
            label_temp_paths.append((label_temp, item.label_target))
    for temp, target in image_temp_paths:
        temp.rename(target)
        renamed += 1
    for temp, target in label_temp_paths:
        temp.rename(target)
        label_renamed += 1
    return RenameResult(renamed_count=renamed, skipped_count=skipped, label_renamed_count=label_renamed)
