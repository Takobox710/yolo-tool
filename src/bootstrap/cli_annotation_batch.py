from __future__ import annotations

from src.bootstrap.cli_common import _emit_structured, _load_json_payload

def _run_ai_label_cli_impl(argv: list[str]) -> int:
    import threading
    from pathlib import Path

    from src.services.annotation import (
        apply_ai_labeling,
        save_editable_annotations,
        save_labelme_annotations,
    )

    payload = _load_json_payload(argv, "Usage: --yolo-ai-label <config-json>")
    try:
        result = apply_ai_labeling(
            image_items=[Path(path) for path in payload.get("image_items", [])],
            target_images=[Path(path) for path in payload.get("target_images", [])],
            current_image=Path(payload["current_image"]) if payload.get("current_image") else None,
            annotations_dir=Path(payload["annotations_dir"]),
            labels_dir=Path(payload["labels_dir"]),
            model_path=str(payload["model_path"]),
            backend=str(payload.get("backend") or "yolo"),
            confidence=float(payload["confidence"]),
            iou=float(payload["iou"]),
            imgsz=int(payload["imgsz"]),
            range_mode=str(payload["range_mode"]),
            current_index=int(payload.get("current_index", -1)),
            selected_images=[Path(path) for path in payload.get("selected_images", [])],
            process_mode=str(payload["process_mode"]),
            class_mapping={str(k): str(v) for k, v in dict(payload.get("class_mapping", {})).items()},
            class_names=[str(name) for name in payload.get("class_names", [])],
            line_expand_pixels=int(payload["line_expand_pixels"]),
            save_json_fn=save_labelme_annotations,
            save_yolo_fn=save_editable_annotations,
            output_mode=str(payload["output_mode"]),
            auto_convert_yolo=bool(payload["auto_convert_yolo"]),
            sam3_prompts={str(k): str(v) for k, v in dict(payload.get("sam3_prompts", {})).items()},
            sam3_enabled_classes=[str(value) for value in payload.get("sam3_enabled_classes", [])],
            sam3_output_shape=str(payload.get("sam3_output_shape") or "rect"),
            sam3_min_area=int(payload.get("sam3_min_area") or 4),
            sam3_polygon_simplify_ratio=float(
                payload.get("sam3_polygon_simplify_ratio") or 0.002
            ),
            progress_callback=lambda data: _emit_structured("progress", payload=data),
            stop_event=threading.Event(),
        )
        _emit_structured(
            "done",
            result={
                "processed": result.processed,
                "total": result.total,
                "updated_images": [str(path) for path in result.updated_images],
                "skipped_images": [str(path) for path in result.skipped_images],
            },
        )
        return 0
    except Exception as exc:
        _emit_structured("error", message=str(exc))
        return 1

