from __future__ import annotations

import json
import os
from typing import Any

from scr.services.runtime_service import STRUCTURED_OUTPUT_PREFIX
from scr.services.training_service import infer_task_mode_from_config, select_training_model


def _parse_value(raw: str) -> Any:
    text = str(raw)
    lower = text.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    try:
        if "." not in text:
            return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def _parse_key_values(parts: list[str]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for part in parts:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        if key:
            values[key] = _parse_value(value)
    return values


def _emit_structured(event: str, **payload: Any) -> None:
    print(
        f"{STRUCTURED_OUTPUT_PREFIX}"
        + json.dumps({"event": event, **payload}, ensure_ascii=False),
        flush=True,
    )


def _load_json_payload(argv: list[str], usage: str) -> dict[str, Any]:
    if not argv:
        raise SystemExit(usage)
    payload_path = argv[0]
    try:
        text = open(payload_path, "r", encoding="utf-8").read()
    except OSError as exc:
        raise SystemExit(f"无法读取配置文件：{exc}") from exc
    finally:
        try:
            os.unlink(payload_path)
        except OSError:
            pass
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"配置文件不是合法 JSON：{exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("配置文件内容必须是 JSON 对象。")
    return payload


def run_train_cli(argv: list[str]) -> int:
    if len(argv) < 2:
        raise SystemExit("Usage: --yolo-train <detect|obb> train key=value ...")
    task_mode, command, *items = argv
    if command != "train":
        raise SystemExit(f"Unsupported training command: {command}")

    from scr.services.ultralytics_compat import ensure_cv2_highgui_compat

    ensure_cv2_highgui_compat()
    from ultralytics import YOLO

    options = _parse_key_values(items)
    model_path = select_training_model(options)
    if not model_path:
        raise SystemExit("Missing model=... for training")
    options.pop("model", None)
    if task_mode != "obb" and infer_task_mode_from_config(
        {"model": model_path, "pretrained": options.get("pretrained")}
    ) == "obb":
        task_mode = "obb"
    model = YOLO(str(model_path))
    model.train(task=task_mode, **options)
    return 0


def run_export_cli(argv: list[str]) -> int:
    from scr.services.ultralytics_compat import ensure_cv2_highgui_compat

    ensure_cv2_highgui_compat()
    from ultralytics import YOLO

    options = _parse_key_values(argv)
    model_path = options.pop("model", None)
    if not model_path:
        raise SystemExit("Missing model=... for export")
    model = YOLO(str(model_path))
    model.export(**options)
    return 0


def run_val_cli(argv: list[str]) -> int:
    if len(argv) < 2:
        raise SystemExit("Usage: --yolo-val <detect|obb> val key=value ...")
    task_mode, command, *items = argv
    if command != "val":
        raise SystemExit(f"Unsupported validation command: {command}")

    from scr.services.ultralytics_compat import ensure_cv2_highgui_compat

    ensure_cv2_highgui_compat()
    from ultralytics import YOLO

    options = _parse_key_values(items)
    model_path = options.pop("model", None)
    if not model_path:
        raise SystemExit("Missing model=... for validation")
    data_path = options.get("data")
    if not data_path:
        raise SystemExit("Missing data=... for validation")
    if task_mode != "obb" and infer_task_mode_from_config({"model": model_path}) == "obb":
        task_mode = "obb"
    model = YOLO(str(model_path))
    model.val(task=task_mode, **options)
    return 0


def run_model_labels_cli(argv: list[str]) -> int:
    if not argv:
        raise SystemExit("Usage: --yolo-model-labels <model-path>")
    from scr.services.annotation_ai_service import load_model_labels

    labels = load_model_labels(argv[0])
    sys_stdout = json.dumps(labels, ensure_ascii=False)
    print(sys_stdout, flush=True)
    return 0


def run_predict_cli(argv: list[str]) -> int:
    from pathlib import Path

    from PIL import Image
    import cv2

    from scr.services.detection_service import (
        IMAGE_SUFFIXES,
        build_save_dir,
        collect_prediction_sources,
        extract_detection_items,
        release_inference_runtime,
        render_result_image_from_frame,
        save_detection_label_file,
    )
    from scr.services.ultralytics_compat import ensure_cv2_highgui_compat

    config = _load_json_payload(argv, "Usage: --yolo-predict <config-json>")
    ensure_cv2_highgui_compat()
    from ultralytics import YOLO

    mode = config.get("source_mode", "图片文件夹")
    model_path = str(config.get("model_path") or "").strip()
    if not model_path:
        raise SystemExit("请选择一个用于检测的模型。")
    if mode in {"图片文件夹", "图片/视频文件夹", "图片/视频"}:
        paths = collect_prediction_sources(
            mode,
            config.get("source_path", ""),
            dataset_yaml=config.get("data"),
            source_scope=str(config.get("source_scope", "全部图片")),
        )
        if not paths:
            raise SystemExit("未找到可检测的图片或视频，请检查输入源。")
        _emit_structured("progress", message=f"已找到 {len(paths)} 个待检测文件。")
    else:
        paths = []
        _emit_structured("progress", message=f"正在打开摄像头 {config.get('camera_index', 0)}。")

    _emit_structured("progress", message=f"正在加载模型：{Path(model_path).name}")
    model = YOLO(model_path)
    save_dir = build_save_dir(Path(config.get("save_dir", "result/gui_predict")))
    _emit_structured("progress", message=f"检测结果将保存到：{save_dir}")

    live_preview_dir = save_dir / "_live_preview"
    live_preview_dir.mkdir(parents=True, exist_ok=True)

    def serialize_items(items) -> list[dict[str, Any]]:
        return [
            {
                "label": item.label,
                "confidence": item.confidence,
                "center_x": item.center_x,
                "center_y": item.center_y,
                "width": item.width,
                "height": item.height,
                "angle": item.angle,
                "points": item.points,
            }
            for item in items
        ]

    def emit_result(**payload: Any) -> None:
        _emit_structured("result", payload=payload)

    def predict_image(image_path: Path, index: int, total: int) -> None:
        _emit_structured("progress", message=f"正在检测 {index}/{total}：{image_path.name}")
        import time

        start = time.perf_counter()
        result = model.predict(
            source=str(image_path),
            conf=config.get("confidence", 0.25),
            iou=config.get("iou", 0.45),
            imgsz=config.get("imgsz", 640),
            verbose=False,
        )[0]
        elapsed = time.perf_counter() - start
        plotted = result.plot()
        result_path = save_dir / image_path.name
        cv2.imwrite(str(result_path), plotted)
        with Image.open(image_path) as image:
            image_size = image.size
        items = extract_detection_items(result)
        save_detection_label_file(
            save_dir / "labels" / f"{image_path.stem}.txt",
            items,
            image_size[0],
            image_size[1],
        )
        emit_result(
            source_name=image_path.name,
            source_path=str(image_path),
            display_source_path=str(image_path),
            result_path=str(result_path),
            items=serialize_items(items),
            status=f"{index}/{total} {image_path.name}",
            elapsed=elapsed,
            cacheable=True,
        )

    def predict_video(video_source: int | str, source_name: str) -> None:
        import time

        cap = cv2.VideoCapture(video_source)
        if not cap.isOpened():
            raise SystemExit(f"无法打开检测源：{source_name or video_source}")
        frame_index = 0
        stream_mode = isinstance(video_source, int)
        source_frame_path = live_preview_dir / "source.jpg"
        result_frame_path = live_preview_dir / "result.jpg"
        try:
            while cap.isOpened():
                ok, frame = cap.read()
                if not ok:
                    break
                frame_index += 1
                start = time.perf_counter()
                result = model.predict(
                    source=frame,
                    conf=config.get("confidence", 0.25),
                    iou=config.get("iou", 0.45),
                    imgsz=config.get("imgsz", 640),
                    verbose=False,
                )[0]
                elapsed = time.perf_counter() - start
                result_image = render_result_image_from_frame(result, frame)
                cv2.imwrite(str(source_frame_path), frame)
                result_image.save(result_frame_path)
                display_name = (
                    f"{source_name} #{frame_index}"
                    if source_name
                    else (f"摄像头 #{frame_index}" if stream_mode else f"frame {frame_index}")
                )
                emit_result(
                    source_name=display_name,
                    source_path=str(video_source),
                    display_source_path=str(source_frame_path),
                    result_path=str(result_frame_path),
                    items=serialize_items(extract_detection_items(result)),
                    status=display_name,
                    elapsed=elapsed,
                    fps=(1 / elapsed) if elapsed else 0.0,
                    stream_mode=stream_mode,
                    cacheable=False,
                )
        finally:
            cap.release()

    try:
        if mode in {"图片文件夹", "图片/视频文件夹", "图片/视频"}:
            total = len(paths)
            for index, image_path in enumerate(paths, start=1):
                if image_path.suffix.lower() in IMAGE_SUFFIXES:
                    predict_image(image_path, index, total)
                else:
                    predict_video(str(image_path), image_path.name)
        else:
            source = int(config.get("camera_index", 0)) if mode == "摄像头" else config.get("source_path")
            predict_video(source, "")
        _emit_structured("done", ok=True)
        return 0
    except Exception as exc:
        _emit_structured("error", message=str(exc))
        return 1
    finally:
        try:
            del model
        except UnboundLocalError:
            pass
        release_inference_runtime()


def run_ai_label_cli(argv: list[str]) -> int:
    import threading
    from pathlib import Path

    from scr.services.annotation_ai_service import apply_ai_labeling
    from scr.services.editable_annotation_service import (
        save_editable_annotations,
        save_labelme_annotations,
    )

    payload = _load_json_payload(argv, "Usage: --yolo-ai-label <config-json>")
    try:
        result = apply_ai_labeling(
            image_items=[Path(path) for path in payload.get("image_items", [])],
            current_image=Path(payload["current_image"]) if payload.get("current_image") else None,
            annotations_dir=Path(payload["annotations_dir"]),
            labels_dir=Path(payload["labels_dir"]),
            model_path=str(payload["model_path"]),
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
