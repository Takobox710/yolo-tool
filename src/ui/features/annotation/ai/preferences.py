from __future__ import annotations

from pathlib import Path

RANGE_MODES = {"当前图片", "当前及以后图片", "全部未标注图片", "全部图片", "自定义图片"}
PROCESS_MODES = {"追加", "替换"}
SAM3_OUTPUT_SHAPES = {"rect", "obb", "polygon"}


def ai_prelabel_settings(page):
    return page.context.settings.annotation.ai_prelabel


def load_ai_prelabel_preferences(page) -> dict:
    saved = ai_prelabel_settings(page)
    range_mode = str(saved.range_mode or "当前图片")
    if range_mode not in RANGE_MODES:
        range_mode = "当前图片"
    process_mode = str(saved.process_mode or "追加")
    if process_mode not in PROCESS_MODES:
        process_mode = "追加"
    output_shape = str(saved.sam3_output_shape or "rect")
    if output_shape not in SAM3_OUTPUT_SHAPES:
        output_shape = "rect"
    prompts = saved.sam3_prompts if isinstance(saved.sam3_prompts, dict) else {}
    enabled_classes = (
        saved.sam3_enabled_classes
        if isinstance(saved.sam3_enabled_classes, list)
        else []
    )

    selected_images = saved.custom_selected_images
    if not isinstance(selected_images, list):
        selected_images = []
    project_root = page.project_root()
    resolved_images: list[Path] = []
    for raw_path in selected_images:
        try:
            path = Path(str(raw_path).strip())
        except (TypeError, ValueError):
            continue
        resolved = path if path.is_absolute() else project_root / path
        resolved_images.append(resolved.resolve())

    return {
        "model_path": str(saved.model_path).strip(),
        "confidence": float(saved.confidence or 0.50),
        "iou": float(saved.iou or 0.45),
        "sam3_confidence": float(saved.sam3_confidence or 0.50),
        "sam3_dedup_iou": float(saved.sam3_dedup_iou or 0.80),
        "sam3_output_shape": output_shape,
        "sam3_prompts": {str(key): str(value) for key, value in prompts.items()},
        "sam3_enabled_classes": [str(value) for value in enabled_classes],
        "sam3_min_area": max(1, int(saved.sam3_min_area or 4)),
        "sam3_polygon_simplify_ratio": max(
            0.0, float(saved.sam3_polygon_simplify_ratio or 0.002)
        ),
        "range_mode": range_mode,
        "process_mode": process_mode,
        "custom_selected_images": resolved_images,
    }


def preferred_ai_model_text(page, saved_model_path: str) -> str:
    if saved_model_path:
        return saved_model_path
    training_settings = page.context.settings.training
    preferred_model = training_settings.pretrained or training_settings.base_model
    return str(preferred_model or "")


def save_ai_prelabel_preferences(
    page,
    *,
    model_path: str,
    fallback_model_text: str,
    confidence: float,
    iou: float,
    sam3_confidence: float,
    sam3_dedup_iou: float,
    sam3_output_shape: str,
    sam3_prompts: dict[str, str],
    sam3_enabled_classes: list[str],
    sam3_min_area: int,
    sam3_polygon_simplify_ratio: float,
    range_mode: str,
    process_mode: str,
    custom_selected_images: list[Path],
) -> None:
    settings = ai_prelabel_settings(page)
    settings.model_path = model_path or fallback_model_text
    settings.confidence = float(confidence)
    settings.iou = float(iou)
    settings.sam3_confidence = float(sam3_confidence)
    settings.sam3_dedup_iou = float(sam3_dedup_iou)
    settings.sam3_output_shape = str(sam3_output_shape)
    settings.sam3_prompts = {str(key): str(value) for key, value in sam3_prompts.items()}
    settings.sam3_enabled_classes = [str(value) for value in sam3_enabled_classes]
    settings.sam3_min_area = max(1, int(sam3_min_area))
    settings.sam3_polygon_simplify_ratio = max(0.0, float(sam3_polygon_simplify_ratio))
    settings.range_mode = range_mode
    settings.process_mode = process_mode
    project_root = page.project_root().resolve()
    saved_paths: list[str] = []
    for path in custom_selected_images:
        resolved = Path(path).resolve()
        try:
            saved_paths.append(str(resolved.relative_to(project_root)))
        except ValueError:
            saved_paths.append(str(resolved))
    settings.custom_selected_images = saved_paths
    page.save_settings()
