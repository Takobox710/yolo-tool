from __future__ import annotations

from pathlib import Path

RANGE_MODES = {"当前图片", "当前及以后图片", "全部未标注图片", "全部图片", "自定义图片"}
PROCESS_MODES = {"追加", "替换"}


def ai_prelabel_settings(page) -> dict:
    annotation_settings = page.app.settings.setdefault("annotation", {})
    return annotation_settings.setdefault("ai_prelabel", {})


def load_ai_prelabel_preferences(page) -> dict:
    saved = ai_prelabel_settings(page)
    range_mode = str(saved.get("range_mode", "当前图片") or "当前图片")
    if range_mode not in RANGE_MODES:
        range_mode = "当前图片"
    process_mode = str(saved.get("process_mode", "追加") or "追加")
    if process_mode not in PROCESS_MODES:
        process_mode = "追加"

    selected_images = saved.get("custom_selected_images", [])
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
        "model_path": str(saved.get("model_path", "")).strip(),
        "confidence": float(saved.get("confidence", 0.50) or 0.50),
        "iou": float(saved.get("iou", 0.45) or 0.45),
        "range_mode": range_mode,
        "process_mode": process_mode,
        "custom_selected_images": resolved_images,
    }


def preferred_ai_model_text(page, saved_model_path: str) -> str:
    if saved_model_path:
        return saved_model_path
    training_settings = page.app.settings.get("training", {})
    preferred_model = training_settings.get("pretrained", "") or training_settings.get(
        "base_model", ""
    )
    return str(preferred_model or "")


def save_ai_prelabel_preferences(
    page,
    *,
    model_path: str,
    fallback_model_text: str,
    confidence: float,
    iou: float,
    range_mode: str,
    process_mode: str,
    custom_selected_images: list[Path],
) -> None:
    settings = ai_prelabel_settings(page)
    settings["model_path"] = model_path or fallback_model_text
    settings["confidence"] = float(confidence)
    settings["iou"] = float(iou)
    settings["range_mode"] = range_mode
    settings["process_mode"] = process_mode
    project_root = page.project_root().resolve()
    saved_paths: list[str] = []
    for path in custom_selected_images:
        resolved = Path(path).resolve()
        try:
            saved_paths.append(str(resolved.relative_to(project_root)))
        except ValueError:
            saved_paths.append(str(resolved))
    settings["custom_selected_images"] = saved_paths
    page.save_settings()
