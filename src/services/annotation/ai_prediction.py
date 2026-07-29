from __future__ import annotations

from pathlib import Path

from src.services.annotation.editable_document import EditableAnnotation
from src.services.annotation.sam3_text import (
    Sam3TextRuntime,
    _deduplicate_candidates,
    normalize_sam3_prompts,
    sam3_annotations_from_masks,
)
from src.services.validation.prediction_runner import extract_detection_items


def predict_annotations_for_image(
    image_path: Path,
    model,
    confidence: float,
    iou: float,
    imgsz: int,
    class_mapping: dict[str, str],
    class_names: list[str],
) -> tuple[list[EditableAnnotation], list[str], list[str]]:
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


def predict_sam3_annotations_for_image(
    image_path: Path,
    runtime: Sam3TextRuntime,
    confidence: float,
    dedup_iou: float,
    output_shape: str,
    prompts: dict[str, str],
    enabled_classes: list[str],
    class_names: list[str],
    minimum_area: int,
    simplification_ratio: float,
) -> tuple[list[EditableAnnotation], dict[str, int]]:
    prompt_rows = normalize_sam3_prompts(class_names, prompts, enabled_classes)
    if not prompt_rows:
        raise ValueError("请至少启用一个带有文本提示词的项目类别。")
    candidates = []
    raw_count = 0
    area_filtered = 0
    order = 0
    runtime.set_image(image_path)
    for class_id, _class_name, prompt in prompt_rows:
        masks, scores = runtime.predict_prompt(prompt, confidence)
        raw_count += len(scores)
        converted, filtered = sam3_annotations_from_masks(
            masks,
            scores,
            class_id,
            output_shape,
            minimum_area,
            simplification_ratio,
            order,
        )
        area_filtered += filtered
        order += len(scores)
        candidates.extend(converted)
    accepted, overlap_filtered = _deduplicate_candidates(candidates, dedup_iou)
    annotations = [
        EditableAnnotation(
            class_id=candidate.class_id,
            shape="rect" if output_shape == "rect" else output_shape,
            points=list(candidate.points),
        )
        for candidate in accepted
    ]
    return annotations, {
        "raw_count": raw_count,
        "area_filtered": area_filtered,
        "overlap_filtered": overlap_filtered,
    }



