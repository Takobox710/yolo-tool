from __future__ import annotations

import json

from src.bootstrap.cli_common import _emit_structured
from src.bootstrap.runtime_protocol import emit_runtime_error, emit_runtime_response

def _run_ai_runtime_cli_impl(argv: list[str]) -> int:
    import sys
    import threading
    from pathlib import Path

    from src.services.annotation import (
        apply_ai_labeling,
        extract_model_labels,
        save_editable_annotations,
        save_labelme_annotations,
    )
    from src.services.validation import release_inference_runtime
    from src.services.ultralytics_compat import ensure_cv2_highgui_compat

    del argv

    ensure_cv2_highgui_compat()

    active_model = None
    active_model_path = ""
    active_backend = ""

    emit_response = emit_runtime_response
    emit_error = emit_runtime_error

    def ensure_model(model_path: str, backend: str):
        nonlocal active_model, active_model_path, active_backend
        resolved_path = str(model_path).strip()
        if not resolved_path:
            raise ValueError("缺少模型文件。")
        backend = str(backend or "yolo").strip().lower()
        if active_model is not None and active_model_path == resolved_path and active_backend == backend:
            return active_model
        if active_model is not None:
            if hasattr(active_model, "close"):
                active_model.close()
            else:
                del active_model
            active_model = None
            active_model_path = ""
            active_backend = ""
            release_inference_runtime()
        if backend == "sam3":
            from src.services.annotation.sam3_text import Sam3TextRuntime

            active_model = Sam3TextRuntime()
            active_model.load_model(resolved_path)
        else:
            from ultralytics import YOLO

            active_model = YOLO(resolved_path)
        active_model_path = resolved_path
        active_backend = backend
        return active_model

    try:
        for raw_line in sys.stdin:
            line = str(raw_line).strip()
            if not line:
                continue
            try:
                command = json.loads(line)
            except json.JSONDecodeError:
                continue

            request_id = str(command.get("request_id") or "")
            action = str(command.get("action") or "")

            try:
                if action == "shutdown":
                    return 0
                if action == "load_model_labels":
                    model_path = str(command.get("model_path") or "")
                    labels = extract_model_labels(ensure_model(model_path, "yolo"))
                    emit_response(
                        request_id,
                        {"labels": labels, "model_path": model_path},
                    )
                    continue
                if action == "apply_ai_labeling":
                    payload = dict(command.get("payload") or {})
                    model_path = str(payload.get("model_path") or "")
                    backend = str(payload.get("backend") or "yolo")
                    model = ensure_model(model_path, backend)
                    result = apply_ai_labeling(
                        image_items=[Path(path) for path in payload.get("image_items", [])],
                        target_images=[Path(path) for path in payload.get("target_images", [])],
                        current_image=Path(payload["current_image"]) if payload.get("current_image") else None,
                        annotations_dir=Path(payload["annotations_dir"]),
                        labels_dir=Path(payload["labels_dir"]),
                        model_path=model_path,
                        backend=backend,
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
                        progress_callback=lambda data: _emit_structured(
                            "runtime_progress",
                            request_id=request_id,
                            payload=data,
                        ),
                        stop_event=threading.Event(),
                        model=model,
                    )
                    emit_response(
                        request_id,
                        {
                            "processed": result.processed,
                            "total": result.total,
                            "updated_images": [str(path) for path in result.updated_images],
                            "skipped_images": [str(path) for path in result.skipped_images],
                        },
                    )
                    continue
                emit_error(request_id, f"不支持的 AI 运行时命令：{action}")
            except Exception as exc:
                emit_error(request_id, str(exc))
        return 0
    finally:
        if active_model is not None:
            if hasattr(active_model, "close"):
                active_model.close()
            else:
                del active_model
            release_inference_runtime()

