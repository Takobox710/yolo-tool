from __future__ import annotations

from typing import Any, Callable

from src.bootstrap.cli_common import _emit_structured, _load_json_payload, _parse_key_values
from src.services.training import infer_task_mode_from_config, infer_task_mode_from_model

def _run_val_cli_impl(argv: list[str]) -> int:
    if len(argv) < 2:
        raise SystemExit("Usage: --yolo-val <detect|obb|seg> val key=value ...")
    task_mode, command, *items = argv
    if task_mode not in {"detect", "obb", "seg"}:
        raise SystemExit("验证任务类型必须是 detect、obb 或 seg")
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
    inferred_mode = infer_task_mode_from_config({"model": model_path})
    if task_mode == "detect" and inferred_mode in {"obb", "seg"}:
        task_mode = inferred_mode
    model = YOLO(str(model_path))
    model.val(task=task_mode, **options)
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
                "class_id": item.class_id,
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
            infer_task_mode_from_model(model_path),
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



def run_val(argv: list[str]) -> int:
    return _run_val_cli_impl(argv)


def run_predict(argv: list[str], emit: Callable[..., None] | None = None) -> int:
    if emit is None:
        return _run_predict_cli_impl(argv)
    previous = globals()["_emit_structured"]
    globals()["_emit_structured"] = emit
    try:
        return _run_predict_cli_impl(argv)
    finally:
        globals()["_emit_structured"] = previous


__all__ = ["run_predict", "run_val"]
