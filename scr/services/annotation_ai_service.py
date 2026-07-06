from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image

from scr.services.detection_service import extract_detection_items
from scr.services.ultralytics_compat import ensure_cv2_highgui_compat
from scr.ui.helpers import find_training_model_names, resolve_training_model_reference

if TYPE_CHECKING:
    from scr.ui.views.annotation import EditableAnnotation


@dataclass
class AiLabelRange:
    mode: str


@dataclass
class AiLabelResult:
    processed: int
    total: int
    updated_images: list[Path]
    skipped_images: list[Path]


def available_ai_models(project_root: Path) -> list[str]:
    return find_training_model_names(project_root)


def resolve_ai_model_path(model_text: str, project_root: Path) -> str:
    return resolve_training_model_reference(model_text, project_root)


def load_model_labels(model_path: str) -> list[str]:
    ensure_cv2_highgui_compat()
    from ultralytics import YOLO

    model = YOLO(model_path)
    names = getattr(model, "names", {})
    if isinstance(names, dict):
        return [str(names[key]).strip() for key in sorted(names) if str(names[key]).strip()]
    if isinstance(names, (list, tuple)):
        return [str(name).strip() for name in names if str(name).strip()]
    return []


def annotation_exists(json_path: Path, yolo_path: Path) -> bool:
    if json_path.exists():
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return False
        return bool(payload.get("shapes"))
    if yolo_path.exists():
        try:
            return any(line.strip() for line in yolo_path.read_text(encoding="utf-8").splitlines())
        except OSError:
            return False
    return False


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


def merge_ai_annotations(
    current: list["EditableAnnotation"],
    incoming: list["EditableAnnotation"],
    process_mode: str,
) -> list["EditableAnnotation"]:
    if str(process_mode).strip() == "替换":
        return list(incoming)
    return list(current) + list(incoming)


def predict_annotations_for_image(
    image_path: Path,
    model,
    confidence: float,
    iou: float,
    imgsz: int,
    class_mapping: dict[str, str],
    class_names: list[str],
) -> tuple[list[EditableAnnotation], list[str], list[str]]:
    from scr.ui.views.annotation import EditableAnnotation
    result = model.predict(
        source=str(image_path),
        conf=confidence,
        iou=iou,
        imgsz=imgsz,
        verbose=False,
    )[0]
    items = extract_detection_items(result)
    model_labels = sorted(
        {
            str(getattr(item, "label", "")).strip()
            for item in items
            if str(getattr(item, "label", "")).strip()
        }
    )
    names = list(class_names)
    annotations: list[EditableAnnotation] = []
    for item in items:
        raw_label = str(item.label or "").strip()
        target_label = class_mapping.get(raw_label, "")
        if not target_label:
            continue
        if target_label not in names:
            names.append(target_label)
        class_id = names.index(target_label)
        shape = "obb" if abs(float(item.angle or 0.0)) > 1e-6 else "rect"
        annotations.append(
            EditableAnnotation(
                class_id=class_id,
                shape=shape,
                points=[(float(x), float(y)) for x, y in item.points[:4]],
            )
        )
    return annotations, names, model_labels


def apply_ai_labeling(
    image_items: list[Path],
    current_image: Path | None,
    annotations_dir: Path,
    labels_dir: Path,
    *,
    model_path: str,
    confidence: float,
    iou: float,
    imgsz: int,
    range_mode: str,
    current_index: int = -1,
    selected_images: list[Path] | None = None,
    process_mode: str,
    class_mapping: dict[str, str],
    class_names: list[str],
    line_expand_pixels: int,
    save_json_fn,
    save_yolo_fn,
    output_mode: str,
    auto_convert_yolo: bool,
    progress_callback,
    stop_event: threading.Event,
) -> AiLabelResult:
    from scr.ui.views.annotation import load_labelme_annotations
    ensure_cv2_highgui_compat()
    from ultralytics import YOLO

    targets = collect_ai_target_images(
        image_items,
        current_image,
        annotations_dir,
        labels_dir,
        range_mode,
        current_index=current_index,
        selected_images=selected_images,
    )
    model = YOLO(model_path)
    updated_images: list[Path] = []
    skipped_images: list[Path] = []
    names = list(class_names)
    total = len(targets)

    for index, image_path in enumerate(targets, start=1):
        if stop_event.is_set():
            break
        json_path = annotations_dir / f"{image_path.stem}.json"
        yolo_path = labels_dir / f"{image_path.stem}.txt"
        try:
            with Image.open(image_path) as image:
                image_size = image.size
        except OSError:
            skipped_images.append(image_path)
            progress_callback(
                {
                    "type": "log",
                    "message": f"跳过：无法打开图片 {image_path.name}",
                    "index": index,
                    "total": total,
                }
            )
            continue
        current_annotations, names = load_labelme_annotations(
            image_size,
            json_path,
            names,
            line_expand_pixels,
        )
        detected, names, model_labels = predict_annotations_for_image(
            image_path,
            model,
            confidence,
            iou,
            imgsz,
            class_mapping,
            names,
        )
        merged = merge_ai_annotations(current_annotations, detected, process_mode)
        save_json_fn(image_size, json_path, image_path, merged, names)
        if auto_convert_yolo:
            save_yolo_fn(image_size, yolo_path, merged, output_mode)
        updated_images.append(image_path)
        progress_callback(
            {
                "type": "progress",
                "index": index,
                "total": total,
                "image_name": image_path.name,
                "result_count": len(detected),
                "model_labels": model_labels,
                "class_names": names,
            }
        )

    return AiLabelResult(
        processed=len(updated_images),
        total=total,
        updated_images=updated_images,
        skipped_images=skipped_images,
    )
