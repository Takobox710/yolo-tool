from __future__ import annotations

from pathlib import Path

from src.services.annotation.file_index import annotation_exists


def collect_ai_target_images(
    image_items: list[Path],
    current_image: Path | None,
    annotations_dir: Path,
    labels_dir: Path,
    range_mode: str,
    *,
    current_index: int = -1,
    selected_images: list[Path] | None = None,
) -> list[Path]:
    mode = str(range_mode).strip()
    if mode == "当前图片":
        return [current_image] if current_image is not None else []
    if mode == "当前及以后图片":
        if not image_items:
            return []
        index = current_index
        if index < 0 and current_image is not None:
            try:
                index = image_items.index(current_image)
            except ValueError:
                index = -1
        if index < 0:
            return []
        return list(image_items[index:])
    if mode == "自定义图片":
        selected_set = {Path(path).resolve() for path in (selected_images or [])}
        return [path for path in image_items if Path(path).resolve() in selected_set]
    if mode == "全部未标注图片":
        return [
            path
            for path in image_items
            if not annotation_exists(
                annotations_dir / f"{path.stem}.json",
                labels_dir / f"{path.stem}.txt",
            )
        ]
    return list(image_items)


def normalize_ai_target_images(
    image_items: list[Path],
    target_images: list[Path] | None,
) -> list[Path]:
    if target_images is None:
        return []
    target_set = {Path(path).resolve() for path in target_images}
    return [path for path in image_items if Path(path).resolve() in target_set]


def merge_ai_annotations(
    current: list["EditableAnnotation"],
    incoming: list["EditableAnnotation"],
    process_mode: str,
) -> list["EditableAnnotation"]:
    if str(process_mode).strip() == "替换":
        return list(incoming)
    return list(current) + list(incoming)



