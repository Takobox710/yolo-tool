from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from src.services.validation.model_catalog import (
    IMAGE_SUFFIXES,
    SOURCE_SUFFIXES,
    VIDEO_SUFFIXES,
    build_detection_log_message,
    detection_counter_text,
    find_result_model_paths,
    is_live_source_mode,
    scan_candidate_models,
    should_store_detection_history,
)
from src.services.validation.rendering import (
    DetectionItem,
    build_save_dir,
    extract_detection_items,
    normalize_detection_item,
    render_result_image_from_frame,
    save_detection_label_file,
)
from src.services.validation.runtime_cleanup import release_inference_runtime
from src.services.validation.source_collectors import (
    collect_dataset_prediction_sources,
    collect_prediction_sources,
)


def run_prediction(
    config: dict,
    stop_event,
    callback: Callable[[dict], None],
    progress_callback: Callable[[str], None] | None = None,
) -> None:
    from PIL import Image
    import cv2
    from src.services.ultralytics_compat import ensure_cv2_highgui_compat

    def progress(message: str) -> None:
        if progress_callback is not None:
            progress_callback(message)

    ensure_cv2_highgui_compat()
    from ultralytics import YOLO

    mode = config.get("source_mode", "图片检测")
    model_path = str(config.get("model_path") or "").strip()
    if not model_path:
        raise ValueError("请选择一个用于检测的模型。")
    if mode in {"图片检测", "视频检测", "图片文件夹", "视频文件夹", "图片/视频文件夹", "图片/视频"}:
        paths = collect_prediction_sources(
            mode,
            config.get("source_path", ""),
            dataset_yaml=config.get("data"),
            source_scope=str(config.get("source_scope", "全部图片")),
        )
        if not paths:
            raise ValueError("未找到可检测的图片或视频，请检查输入源。")
        progress(f"已找到 {len(paths)} 个待检测文件。")
    else:
        paths = []
        progress(f"正在打开摄像头 {config.get('camera_index', 0)}。")
    progress(f"正在加载模型：{Path(model_path).name}")
    model = YOLO(model_path)
    save_dir = build_save_dir(Path(config.get("save_dir", "result/gui_predict")))
    progress(f"检测结果将保存到：{save_dir}")

    def predict_image(image_path: Path, index: int, total: int) -> None:
        progress(f"正在检测 {index}/{total}：{image_path.name}")
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
        original = Image.open(image_path).convert("RGB")
        items = extract_detection_items(result)
        save_detection_label_file(
            save_dir / "labels" / f"{image_path.stem}.txt",
            items,
            original.width,
            original.height,
        )
        callback(
            {
                "source_image": original,
                "result_image": Image.fromarray(cv2.cvtColor(plotted, cv2.COLOR_BGR2RGB)),
                "items": items,
                "status": f"{index}/{total} {image_path.name}",
                "source_name": image_path.name,
                "source_path": str(image_path),
                "result_path": str(result_path),
                "elapsed": elapsed,
            }
        )

    def predict_video(video_source: int | str, source_name: str) -> None:
        cap = cv2.VideoCapture(video_source)
        if not cap.isOpened():
            raise ValueError(f"无法打开检测源：{source_name or video_source}")
        frame_index = 0
        stream_mode = isinstance(video_source, int)
        try:
            while cap.isOpened() and not stop_event.is_set():
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
                display_name = f"{source_name} #{frame_index}" if source_name else (f"摄像头 #{frame_index}" if stream_mode else f"frame {frame_index}")
                callback(
                    {
                        "source_image": Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)),
                        "result_image": render_result_image_from_frame(result, frame),
                        "items": extract_detection_items(result),
                        "status": display_name,
                        "source_name": display_name,
                        "source_path": str(video_source),
                        "elapsed": elapsed,
                        "fps": (1 / elapsed) if elapsed else 0.0,
                        "stream_mode": stream_mode,
                    }
                )
        finally:
            cap.release()

    try:
        if mode in {"图片检测", "视频检测", "图片文件夹", "视频文件夹", "图片/视频文件夹", "图片/视频"}:
            total = len(paths)
            for index, image_path in enumerate(paths, start=1):
                if stop_event.is_set():
                    break
                if image_path.suffix.lower() in IMAGE_SUFFIXES:
                    predict_image(image_path, index, total)
                else:
                    predict_video(str(image_path), image_path.name)
        else:
            source = int(config.get("camera_index", 0)) if mode == "摄像头" else config.get("source_path")
            predict_video(source, "")
    finally:
        del model
        release_inference_runtime()

