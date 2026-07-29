from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image

from src.services.annotation.editable_document import (
    EditableAnnotation,
    load_labelme_annotations,
)
from src.services.annotation.sam3_text import Sam3TextRuntime
from src.services.training.model_resolution import (
    find_training_model_names,
    resolve_training_model_reference,
)
from src.services.ultralytics_compat import ensure_cv2_highgui_compat
from src.services.validation.prediction_runner import release_inference_runtime


from src.services.annotation.ai_prediction import (
    predict_annotations_for_image,
    predict_sam3_annotations_for_image,
)
from src.services.annotation.ai_targets import (
    collect_ai_target_images,
    merge_ai_annotations,
    normalize_ai_target_images,
)

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


def extract_model_labels(model) -> list[str]:
    names = getattr(model, "names", {})
    if isinstance(names, dict):
        return [str(names[key]).strip() for key in sorted(names) if str(names[key]).strip()]
    if isinstance(names, (list, tuple)):
        return [str(name).strip() for name in names if str(name).strip()]
    return []


def load_model_labels(model_path: str) -> list[str]:
    ensure_cv2_highgui_compat()
    from ultralytics import YOLO

    model = YOLO(model_path)
    try:
        return extract_model_labels(model)
    finally:
        del model
        release_inference_runtime()
def apply_ai_labeling(
    image_items: list[Path],
    current_image: Path | None,
    annotations_dir: Path,
    labels_dir: Path,
    *,
    model_path: str,
    backend: str = "yolo",
    confidence: float,
    iou: float,
    imgsz: int,
    range_mode: str,
    current_index: int = -1,
    selected_images: list[Path] | None = None,
    target_images: list[Path] | None = None,
    process_mode: str,
    class_mapping: dict[str, str],
    class_names: list[str],
    line_expand_pixels: int,
    save_json_fn,
    save_yolo_fn,
    output_mode: str,
    auto_convert_yolo: bool,
    sam3_prompts: dict[str, str] | None = None,
    sam3_enabled_classes: list[str] | None = None,
    sam3_output_shape: str = "rect",
    sam3_min_area: int = 4,
    sam3_polygon_simplify_ratio: float = 0.002,
    progress_callback,
    stop_event: threading.Event,
    model=None,
) -> AiLabelResult:
    backend = str(backend or "yolo").strip().lower()
    if backend not in {"yolo", "sam3"}:
        raise ValueError(f"不支持的 AI 模型类型：{backend}")
    if backend == "yolo":
        ensure_cv2_highgui_compat()
        from ultralytics import YOLO
    else:
        YOLO = None

    targets = normalize_ai_target_images(image_items, target_images)
    if not targets:
        targets = collect_ai_target_images(
            image_items,
            current_image,
            annotations_dir,
            labels_dir,
            range_mode,
            current_index=current_index,
            selected_images=selected_images,
        )
    active_model = model
    owns_model = active_model is None
    if active_model is None:
        active_model = Sam3TextRuntime() if backend == "sam3" else YOLO(model_path)
        if backend == "sam3":
            active_model.load_model(model_path)
    try:
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
            if backend == "sam3":
                detected, stats = predict_sam3_annotations_for_image(
                    image_path,
                    active_model,
                    confidence,
                    iou,
                    sam3_output_shape,
                    dict(sam3_prompts or {}),
                    list(sam3_enabled_classes or []),
                    names,
                    sam3_min_area,
                    sam3_polygon_simplify_ratio,
                )
                model_labels = []
            else:
                detected, names, model_labels = predict_annotations_for_image(
                    image_path,
                    active_model,
                    confidence,
                    iou,
                    imgsz,
                    class_mapping,
                    names,
                )
                stats = {}
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
                    "sam3_stats": stats,
                }
            )

        return AiLabelResult(
            processed=len(updated_images),
            total=total,
            updated_images=updated_images,
            skipped_images=skipped_images,
        )
    finally:
        if owns_model:
            if hasattr(active_model, "close"):
                active_model.close()
            else:
                del active_model
                release_inference_runtime()
