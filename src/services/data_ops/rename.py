from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp"}


def natural_sort_key(path: Path) -> list[object]:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", Path(path).name)]


@dataclass
class RenamePlanItem:
    source: Path
    target: Path
    index: int
    old_name: str
    new_name: str
    conflict: bool
    labelme_source: Path | None = None
    labelme_target: Path | None = None
    labelme_conflict: bool = False
    labelme_note: str = ""
    label_source: Path | None = None
    label_target: Path | None = None
    label_conflict: bool = False
    note: str = ""


@dataclass
class RenameResult:
    renamed_count: int
    skipped_count: int
    labelme_renamed_count: int = 0
    label_renamed_count: int = 0


def _label_plan(
    source: Path,
    new_name: str,
    labels_dir: Path | None,
    suffix: str,
    enabled: bool,
) -> tuple[Path | None, Path | None, bool, str]:
    if not enabled or labels_dir is None:
        return None, None, False, ""
    label_source = Path(labels_dir) / f"{source.stem}{suffix}"
    label_target = Path(labels_dir) / f"{Path(new_name).stem}{suffix}"
    if not label_source.exists():
        return None, None, False, "未找到同名标注"
    if label_target.exists() and label_target.resolve() != label_source.resolve():
        return label_source, label_target, True, f"标注目标已存在: {label_target.name}"
    return label_source, label_target, False, ""


def preview_rename(
    folder: Path,
    prefix: str,
    start: int,
    padding: int,
    labels_dir: Path | None = None,
    include_labels: bool = False,
    labelme_dir: Path | None = None,
    include_labelme: bool = False,
) -> list[RenamePlanItem]:
    files = sorted(
        (path for path in Path(folder).iterdir() if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES),
        key=natural_sort_key,
    )
    plan: list[RenamePlanItem] = []
    for offset, source in enumerate(files):
        number = start + offset
        new_name = f"{prefix}{number:0{padding}d}{source.suffix.lower()}"
        target = source.with_name(new_name)
        conflict = target.exists() and target.resolve() != source.resolve()
        labelme_source, labelme_target, labelme_conflict, labelme_note = _label_plan(
            source, new_name, labelme_dir, ".json", include_labelme
        )
        label_source, label_target, label_conflict, note = _label_plan(
            source, new_name, labels_dir, ".txt", include_labels
        )
        plan.append(
            RenamePlanItem(
                source=source,
                target=target,
                index=offset + 1,
                old_name=source.name,
                new_name=new_name,
                conflict=conflict,
                labelme_source=labelme_source,
                labelme_target=labelme_target,
                labelme_conflict=labelme_conflict,
                labelme_note=labelme_note,
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
    labelme_renamed = 0
    label_renamed = 0
    if any(item.labelme_conflict or item.label_conflict for item in plan):
        return RenameResult(renamed_count=0, skipped_count=len(plan))
    image_temp_paths: list[tuple[Path, Path]] = []
    labelme_temp_paths: list[tuple[Path, Path]] = []
    label_temp_paths: list[tuple[Path, Path]] = []
    for item in plan:
        temp = item.source.with_name(f".__rename_tmp_{item.index}_{item.source.name}")
        item.source.rename(temp)
        image_temp_paths.append((temp, item.target))
        if item.labelme_source and item.labelme_target:
            labelme_temp = item.labelme_source.with_name(f".__rename_tmp_{item.index}_{item.labelme_source.name}")
            item.labelme_source.rename(labelme_temp)
            labelme_temp_paths.append((labelme_temp, item.labelme_target))
        if item.label_source and item.label_target:
            label_temp = item.label_source.with_name(f".__rename_tmp_{item.index}_{item.label_source.name}")
            item.label_source.rename(label_temp)
            label_temp_paths.append((label_temp, item.label_target))
    for temp, target in image_temp_paths:
        temp.rename(target)
        renamed += 1
    for temp, target in labelme_temp_paths:
        temp.rename(target)
        labelme_renamed += 1
    for temp, target in label_temp_paths:
        temp.rename(target)
        label_renamed += 1
    return RenameResult(
        renamed_count=renamed,
        skipped_count=skipped,
        labelme_renamed_count=labelme_renamed,
        label_renamed_count=label_renamed,
    )
