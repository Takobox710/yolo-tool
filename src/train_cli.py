from __future__ import annotations

import json
import os
from typing import Any

from src.services.runtime import STRUCTURED_OUTPUT_PREFIX
from src.services.training import infer_task_mode_from_config, select_training_model


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


def _run_train_cli_impl(argv: list[str]) -> int:
    if len(argv) < 2:
        raise SystemExit("Usage: --yolo-train <detect|obb> train key=value ...")
    task_mode, command, *items = argv
    if command != "train":
        raise SystemExit(f"Unsupported training command: {command}")

    from src.services.ultralytics_compat import ensure_cv2_highgui_compat

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


def _run_export_cli_impl(argv: list[str]) -> int:
    os.environ["YOLO_AUTOINSTALL"] = "false"
    from src.services.ultralytics_compat import ensure_cv2_highgui_compat
    from src.services.model_export import export_model_to_directory

    ensure_cv2_highgui_compat()
    from ultralytics import YOLO

    options = _parse_key_values(argv)
    if not options.get("model"):
        raise SystemExit("Missing model=... for export")
    try:
        result = export_model_to_directory(
            options,
            yolo_factory=YOLO,
            progress=lambda message: _emit_structured("progress", message=message),
        )
        _emit_structured("done", ok=True, result_path=str(result))
        return 0
    except Exception as exc:
        _emit_structured("error", message=str(exc))
        return 1


def _run_export_probe_cli_impl(argv: list[str]) -> int:
    from importlib import metadata
    import importlib
    from src.services.model_export.package import EXPORT_PROTOCOL_VERSION

    del argv
    distributions = {
        "openvino": "openvino",
        "ncnn": "ncnn",
        "pnnx": "pnnx",
        "tensorrt": "tensorrt",
    }
    versions: dict[str, str] = {}
    missing: list[str] = []
    for module_name, distribution in distributions.items():
        try:
            importlib.import_module(module_name)
        except Exception as exc:
            missing.append(module_name)
            versions[module_name] = f"不可用：{exc}"
            continue
        try:
            versions[module_name] = metadata.version(distribution)
        except metadata.PackageNotFoundError:
            versions[module_name] = "已安装"
    payload = {
        "protocol_version": EXPORT_PROTOCOL_VERSION,
        "ok": not missing,
        "modules": versions,
        "missing": missing,
    }
    print(json.dumps(payload, ensure_ascii=False), flush=True)
    return 0 if not missing else 1


def _run_install_model_export_package_cli_impl(argv: list[str]) -> int:
    from src.services.model_export import install_extension_package

    options = _parse_key_values(argv)
    package_path = str(options.get("package") or "").strip()
    if not package_path:
        raise SystemExit("Usage: --install-model-export-package package=<archive>")
    try:
        installed = install_extension_package(package_path)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(
        json.dumps(
            {"ok": True, "version": installed.version, "root": str(installed.root)},
            ensure_ascii=False,
        )
    )
    return 0


def _run_migrate_legacy_extension_cli_impl(argv: list[str]) -> int:
    from src.services.runtime import migrate_legacy_extensions

    del argv
    try:
        migrated = migrate_legacy_extensions()
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"ok": True, "migrated": migrated}, ensure_ascii=False))
    return 0


def _run_runtime_probe_cli_impl(argv: list[str]) -> int:
    from src.services.runtime.release_manifest import check_runtime_compatibility

    del argv
    compatibility = check_runtime_compatibility()
    print(
        json.dumps(
            {
                "ok": compatibility.compatible,
                "runtime_version": compatibility.runtime_version,
                "required_runtime_version": compatibility.required_runtime_version,
                "reason": compatibility.reason,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return 0 if compatibility.compatible else 1


def _run_remove_managed_models_cli_impl(argv: list[str]) -> int:
    from src.services.runtime import remove_managed_models
    from src.shared.paths import ROOT

    del argv
    try:
        removed = remove_managed_models(ROOT)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(
        json.dumps(
            {"ok": True, "removed": [str(path) for path in removed]},
            ensure_ascii=False,
        )
    )
    return 0


def _run_val_cli_impl(argv: list[str]) -> int:
    if len(argv) < 2:
        raise SystemExit("Usage: --yolo-val <detect|obb> val key=value ...")
    task_mode, command, *items = argv
    if command != "val":
        raise SystemExit(f"Unsupported validation command: {command}")

    from src.services.ultralytics_compat import ensure_cv2_highgui_compat

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


def _run_model_labels_cli_impl(argv: list[str]) -> int:
    if not argv:
        raise SystemExit("Usage: --yolo-model-labels <model-path>")
    from src.services.annotation import load_model_labels

    labels = load_model_labels(argv[0])
    sys_stdout = json.dumps(labels, ensure_ascii=False)
    print(sys_stdout, flush=True)
    return 0


def _run_predict_cli_impl(argv: list[str]) -> int:
    from pathlib import Path

    from PIL import Image
    import cv2

    from src.services.validation import (
        IMAGE_SUFFIXES,
        build_save_dir,
        collect_prediction_sources,
        extract_detection_items,
        is_live_source_mode,
        release_inference_runtime,
        save_detection_label_file,
    )
    from src.services.ultralytics_compat import ensure_cv2_highgui_compat

    config = _load_json_payload(argv, "Usage: --yolo-predict <config-json>")
    ensure_cv2_highgui_compat()
    from ultralytics import YOLO

    mode = config.get("source_mode", "图片检测")
    model_path = str(config.get("model_path") or "").strip()
    if not model_path:
        raise SystemExit("请选择一个用于检测的模型。")
    if mode in {"图片检测", "视频检测", "图片文件夹", "视频文件夹", "图片/视频文件夹", "图片/视频"}:
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
    save_dir = build_save_dir(
        Path(config.get("save_dir", "result/gui_predict")),
        create_labels=any(path.suffix.lower() in IMAGE_SUFFIXES for path in paths),
    )
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
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        video_fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        source_frame_path = live_preview_dir / "source.jpg"
        result_frame_path = live_preview_dir / "result.jpg"
        writer = None
        result_path = None
        last_report_time = time.perf_counter()
        last_report_frame = 0
        last_payload = None
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
                plotted = result.plot(img=frame.copy())
                if not stream_mode:
                    if writer is None:
                        result_path = save_dir / f"{Path(source_name).stem}_result.mp4"
                        height, width = plotted.shape[:2]
                        writer = cv2.VideoWriter(
                            str(result_path),
                            cv2.VideoWriter_fourcc(*"mp4v"),
                            video_fps if video_fps > 0 else 25.0,
                            (width, height),
                        )
                        if not writer.isOpened():
                            raise SystemExit(f"无法创建视频结果文件：{result_path}")
                    writer.write(plotted)
                display_name = (
                    f"{source_name} #{frame_index}"
                    if source_name
                    else (f"摄像头 #{frame_index}" if stream_mode else f"frame {frame_index}")
                )
                cv2.imwrite(str(source_frame_path), frame)
                result_image = Image.fromarray(
                    cv2.cvtColor(plotted, cv2.COLOR_BGR2RGB)
                )
                result_image.save(result_frame_path)
                last_payload = {
                    "source_name": display_name,
                    "source_path": str(video_source),
                    "display_source_path": str(source_frame_path),
                    "result_path": str(result_path or result_frame_path),
                    "items": serialize_items(extract_detection_items(result)),
                    "status": display_name,
                    "elapsed": elapsed,
                    "fps": (1 / elapsed) if elapsed else 0.0,
                    "stream_mode": stream_mode,
                    "video_mode": not stream_mode,
                    "cacheable": False,
                }
                now = time.perf_counter()
                if stream_mode or now - last_report_time >= 1.0:
                    frames_last_second = frame_index - last_report_frame
                    percent = (
                        min(100, int(frame_index * 100 / total_frames))
                        if total_frames > 0
                        else 0
                    )
                    if not stream_mode:
                        _emit_structured(
                            "video_progress",
                            payload={
                                "percent": percent,
                                "frame": frame_index,
                                "total_frames": total_frames,
                                "frames_last_second": frames_last_second,
                                "source_path": str(video_source),
                            },
                        )
                    emit_result(**last_payload)
                    last_report_time = now
                    last_report_frame = frame_index
            if not stream_mode and last_payload is not None:
                _emit_structured(
                    "video_progress",
                    payload={
                        "percent": 100,
                        "frame": frame_index,
                        "total_frames": total_frames,
                        "frames_last_second": frame_index - last_report_frame,
                        "source_path": str(video_source),
                    },
                )
                if frame_index != last_report_frame:
                    emit_result(**last_payload)
        finally:
            cap.release()
            if writer is not None:
                writer.release()
        if not stream_mode and result_path is not None:
            _emit_structured(
                "video_completed",
                payload={
                    "source_path": str(video_source),
                    "result_path": str(result_path),
                },
            )

    try:
        if mode in {"图片检测", "视频检测", "图片文件夹", "视频文件夹", "图片/视频文件夹", "图片/视频"}:
            total = len(paths)
            for index, image_path in enumerate(paths, start=1):
                if image_path.suffix.lower() in IMAGE_SUFFIXES:
                    predict_image(image_path, index, total)
                else:
                    predict_video(str(image_path), image_path.name)
        else:
            source = (
                int(config.get("camera_index", 0))
                if is_live_source_mode(mode)
                else config.get("source_path")
            )
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

    def emit_response(request_id: str, result: dict[str, Any]) -> None:
        _emit_structured("runtime_response", request_id=request_id, result=result)

    def emit_error(request_id: str, message: str) -> None:
        _emit_structured("runtime_error", request_id=request_id, message=message)

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


def _run_sam_assist_runtime_cli_impl(argv: list[str]) -> int:
    import sys

    from src.services.annotation.sam_runtime import SamAssistRuntime

    del argv
    runtime = SamAssistRuntime()

    def emit_response(request_id: str, result: dict[str, Any]) -> None:
        _emit_structured("runtime_response", request_id=request_id, result=result)

    def emit_error(request_id: str, message: str) -> None:
        _emit_structured("runtime_error", request_id=request_id, message=message)

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
                    emit_response(request_id, {"state": "shutdown"})
                    return 0
                if action == "load_model":
                    result = runtime.load_model(
                        str(command.get("checkpoint_path") or ""),
                        str(command.get("config_name") or ""),
                        int(command.get("model_generation") or 0),
                        str(command.get("runtime_kind") or "sam2"),
                    )
                    emit_response(request_id, result)
                    continue
                if action == "set_image":
                    result = runtime.set_image(
                        str(command.get("image_path") or ""),
                        int(command.get("image_generation") or 0),
                        int(command.get("model_generation") or 0),
                    )
                    emit_response(request_id, result)
                    continue
                if action == "predict_point":
                    result = runtime.predict_point(
                        float(command.get("x") or 0.0),
                        float(command.get("y") or 0.0),
                        int(command.get("image_generation") or 0),
                        int(command.get("model_generation") or 0),
                        bool(command.get("multimask_output", False)),
                        float(command.get("minimum_score") or 0.0),
                        int(command.get("minimum_area") or 4),
                        float(command.get("simplification_ratio") or 0.002),
                    )
                    result["x"] = float(command.get("x") or 0.0)
                    result["y"] = float(command.get("y") or 0.0)
                    emit_response(request_id, result)
                    continue
                emit_error(request_id, f"不支持的 SAM 运行时命令：{action}")
            except Exception as exc:
                emit_error(request_id, str(exc))
        return 0
    finally:
        runtime.close()


def run_train_cli(argv: list[str]) -> int:
    from src.bootstrap.handlers import run_train

    return run_train(argv)


def run_export_cli(argv: list[str]) -> int:
    from src.bootstrap.handlers import run_export

    return run_export(argv)


def run_export_probe_cli(argv: list[str]) -> int:
    from src.bootstrap.handlers import run_export_probe

    return run_export_probe(argv)


def run_install_model_export_package_cli(argv: list[str]) -> int:
    from src.bootstrap.handlers import run_install_model_export_package

    return run_install_model_export_package(argv)


def run_migrate_legacy_extension_cli(argv: list[str]) -> int:
    from src.bootstrap.handlers import run_migrate_legacy_extension

    return run_migrate_legacy_extension(argv)


def run_runtime_probe_cli(argv: list[str]) -> int:
    from src.bootstrap.handlers import run_runtime_probe

    return run_runtime_probe(argv)


def run_remove_managed_models_cli(argv: list[str]) -> int:
    from src.bootstrap.handlers import run_remove_managed_models

    return run_remove_managed_models(argv)


def run_val_cli(argv: list[str]) -> int:
    from src.bootstrap.handlers import run_val

    return run_val(argv)


def run_model_labels_cli(argv: list[str]) -> int:
    from src.bootstrap.handlers import run_model_labels

    return run_model_labels(argv)


def run_predict_cli(argv: list[str]) -> int:
    from src.bootstrap.handlers import run_predict

    return run_predict(argv)


def run_ai_label_cli(argv: list[str]) -> int:
    from src.bootstrap.handlers import run_ai_label

    return run_ai_label(argv)


def run_ai_runtime_cli(argv: list[str]) -> int:
    from src.bootstrap.handlers import run_ai_runtime

    return run_ai_runtime(argv)


def run_sam_assist_runtime_cli(argv: list[str]) -> int:
    from src.bootstrap.handlers import run_sam_assist_runtime

    return run_sam_assist_runtime(argv)
