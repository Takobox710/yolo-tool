from __future__ import annotations

import gc
import math
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import yaml


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp"}
VIDEO_SUFFIXES = {".mp4", ".avi", ".mov", ".mkv"}
SOURCE_SUFFIXES = IMAGE_SUFFIXES | VIDEO_SUFFIXES


def release_inference_runtime() -> None:
    torch = None
    try:
        import torch as _torch

        torch = _torch
    except Exception:
        torch = None
    gc.collect()
    if torch is None:
        return
    try:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
    except Exception:
        pass


def _natural_sort_key(path: Path) -> list[object]:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", path.name)]


@dataclass
class DetectionItem:
    label: str
    confidence: float
    center_x: float
    center_y: float
    width: float
    height: float
    angle: float
    points: list[tuple[float, float]]


def scan_candidate_models(result_dir: Path) -> list[Path]:
    root = Path(result_dir)
    if not root.exists():
        return []
    run_dirs = sorted([path for path in root.glob("train*") if path.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)
    candidates: list[Path] = []
    for run_dir in run_dirs:
        for name in ("best.pt", "last.pt"):
            model = run_dir / "weights" / name
            if model.exists():
                candidates.append(model)
    return candidates


def find_result_model_paths(
    result_dir: Path, *, show_last_training_models: bool = True
) -> list[Path]:
    models = scan_candidate_models(result_dir)
    if show_last_training_models:
        return models
    return [path for path in models if path.name.lower() != "last.pt"]


def is_live_source_mode(source_mode: str) -> bool:
    return str(source_mode).strip() == "摄像头"


def should_store_detection_history(source_mode: str) -> bool:
    return not is_live_source_mode(source_mode)


def detection_counter_text(
    source_mode: str, detect_index: int, result_count: int
) -> str:
    if is_live_source_mode(source_mode):
        return "实时预览"
    if result_count <= 0 or detect_index < 0:
        return "0/0"
    return f"{detect_index + 1}/{result_count}"


def build_detection_log_message(payload: dict) -> str:
    elapsed = float(payload.get("elapsed") or 0.0)
    fps = payload.get("fps")
    if fps is None:
        fps = (1 / elapsed) if elapsed else 0.0
    fps_text = (
        f"实时帧率 FPS: {fps:.1f}"
        if payload.get("stream_mode")
        else f"FPS: {fps:.1f}"
    )
    return (
        f"{payload.get('status')} | 单张耗时: {elapsed * 1000:.1f}ms | "
        f"{fps_text} | 结果: {len(payload.get('items') or [])} 个"
    )


def normalize_detection_item(label: str, confidence: float, points: list[tuple[float, float]]) -> DetectionItem:
    center_x = sum(point[0] for point in points) / len(points)
    center_y = sum(point[1] for point in points) / len(points)
    width = math.dist(points[0], points[1]) if len(points) >= 2 else 0.0
    height = math.dist(points[1], points[2]) if len(points) >= 3 else 0.0
    angle = math.degrees(math.atan2(points[1][1] - points[0][1], points[1][0] - points[0][0])) if len(points) >= 2 else 0.0
    return DetectionItem(label, confidence, center_x, center_y, width, height, angle, points)


def extract_detection_items(result: Any) -> list[DetectionItem]:
    names = getattr(result, "names", {})
    obb = getattr(result, "obb", None)
    if obb is not None and getattr(obb, "xyxyxyxy", None) is not None:
        points_list = obb.xyxyxyxy.cpu().tolist()
        confidences = obb.conf.cpu().tolist() if getattr(obb, "conf", None) is not None else [0.0] * len(points_list)
        classes = obb.cls.cpu().tolist() if getattr(obb, "cls", None) is not None else [0] * len(points_list)
        return [
            normalize_detection_item(
                names.get(int(class_id), str(int(class_id))),
                float(confidence),
                [(float(x), float(y)) for x, y in points],
            )
            for points, confidence, class_id in zip(points_list, confidences, classes)
        ]

    boxes = getattr(result, "boxes", None)
    if boxes is None or getattr(boxes, "xyxy", None) is None:
        return []
    xyxy = boxes.xyxy.cpu().tolist()
    confidences = boxes.conf.cpu().tolist() if getattr(boxes, "conf", None) is not None else [0.0] * len(xyxy)
    classes = boxes.cls.cpu().tolist() if getattr(boxes, "cls", None) is not None else [0] * len(xyxy)
    items: list[DetectionItem] = []
    for box, confidence, class_id in zip(xyxy, confidences, classes):
        x1, y1, x2, y2 = [float(v) for v in box]
        points = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
        items.append(normalize_detection_item(names.get(int(class_id), str(int(class_id))), float(confidence), points))
    return items


def build_save_dir(base_dir: Path) -> Path:
    target = Path(base_dir) / time.strftime("%Y%m%d_%H%M%S")
    target.mkdir(parents=True, exist_ok=True)
    (target / "labels").mkdir(parents=True, exist_ok=True)
    return target


def _normalize_point(value: float, size: int) -> float:
    return 0.0 if size <= 0 else value / float(size)


def save_detection_label_file(
    label_path: Path,
    items: list[DetectionItem],
    image_width: int,
    image_height: int,
) -> None:
    lines: list[str] = []
    for item in items:
        is_obb = len(item.points) >= 4 and abs(item.angle) > 1e-6
        if is_obb:
            coords: list[str] = []
            for x, y in item.points[:4]:
                coords.append(f"{_normalize_point(x, image_width):.6f}")
                coords.append(f"{_normalize_point(y, image_height):.6f}")
            lines.append("0 " + " ".join(coords))
            continue
        lines.append(
            "0 "
            + " ".join(
                [
                    f"{_normalize_point(item.center_x, image_width):.6f}",
                    f"{_normalize_point(item.center_y, image_height):.6f}",
                    f"{_normalize_point(item.width, image_width):.6f}",
                    f"{_normalize_point(item.height, image_height):.6f}",
                ]
            )
        )
    label_path.write_text(
        ("\n".join(lines) + ("\n" if lines else "")), encoding="utf-8"
    )


def render_result_image_from_frame(result: Any, frame) -> Any:
    from PIL import Image
    import cv2

    plotted = result.plot(img=frame.copy())
    return Image.fromarray(cv2.cvtColor(plotted, cv2.COLOR_BGR2RGB))


def _dataset_sort_key(path: Path) -> tuple[str, list[object]]:
    return (str(path.parent).lower(), _natural_sort_key(path))


def _resolve_dataset_entry_path(
    raw_path: str | Path,
    yaml_path: Path,
    dataset_root: Path,
) -> Path:
    path = Path(str(raw_path))
    if path.is_absolute():
        return path
    candidate = dataset_root / path
    if candidate.exists():
        return candidate
    return (yaml_path.parent / path).resolve()


def _collect_media_from_dataset_entry(
    entry: Any,
    yaml_path: Path,
    dataset_root: Path,
) -> list[Path]:
    if isinstance(entry, list):
        items: list[Path] = []
        for value in entry:
            items.extend(_collect_media_from_dataset_entry(value, yaml_path, dataset_root))
        return items
    if not isinstance(entry, str) or not entry.strip():
        return []
    target = _resolve_dataset_entry_path(entry.strip(), yaml_path, dataset_root)
    if not target.exists():
        return []
    if target.is_dir():
        return sorted(
            (
                path
                for path in target.rglob("*")
                if path.is_file() and path.suffix.lower() in SOURCE_SUFFIXES
            ),
            key=_dataset_sort_key,
        )
    if target.suffix.lower() == ".txt":
        lines = target.read_text(encoding="utf-8").splitlines()
        items: list[Path] = []
        for line in lines:
            resolved = _resolve_dataset_entry_path(line.strip(), target, dataset_root)
            if resolved.is_file() and resolved.suffix.lower() in SOURCE_SUFFIXES:
                items.append(resolved)
        return sorted(items, key=_dataset_sort_key)
    if target.is_file() and target.suffix.lower() in SOURCE_SUFFIXES:
        return [target]
    return []


def collect_dataset_prediction_sources(
    dataset_yaml: str | Path,
    source_scope: str = "全部图片",
) -> list[Path]:
    yaml_path = Path(dataset_yaml)
    if not yaml_path.exists() or yaml_path.suffix.lower() not in {".yaml", ".yml"}:
        return []
    try:
        payload = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(payload, dict):
        return []

    dataset_root_value = payload.get("path")
    if dataset_root_value:
        dataset_root = _resolve_dataset_entry_path(dataset_root_value, yaml_path, yaml_path.parent)
    else:
        dataset_root = yaml_path.parent.resolve()

    scope_map = {
        "训练图片": ["train"],
        "验证图片": ["val"],
        "测试图片": ["test"],
        "全部图片": ["train", "val", "test"],
    }
    selected_splits = scope_map.get(str(source_scope).strip(), ["train", "val", "test"])
    results: list[Path] = []
    seen: set[str] = set()
    for split in selected_splits:
        for path in _collect_media_from_dataset_entry(payload.get(split), yaml_path, dataset_root):
            resolved = str(path.resolve())
            if resolved in seen:
                continue
            seen.add(resolved)
            results.append(path.resolve())
    return results


def collect_prediction_sources(
    source_mode: str,
    source_path: str | Path,
    *,
    dataset_yaml: str | Path | None = None,
    source_scope: str = "全部图片",
) -> list[Path]:
    source_text = str(source_path or "").strip()
    source = Path(source_text) if source_text else None
    if source_mode in {"图片文件夹", "图片/视频文件夹"}:
        if source is not None and source.exists() and source.is_dir():
            return sorted(
                (
                    path
                    for path in source.iterdir()
                    if path.is_file() and path.suffix.lower() in SOURCE_SUFFIXES
                ),
                key=_natural_sort_key,
            )
        if dataset_yaml:
            return collect_dataset_prediction_sources(dataset_yaml, source_scope)
        return []
    if source_mode == "图片/视频" and source is not None:
        return [source] if source.is_file() and source.suffix.lower() in SOURCE_SUFFIXES else []
    return []


def run_prediction(
    config: dict,
    stop_event,
    callback: Callable[[dict], None],
    progress_callback: Callable[[str], None] | None = None,
) -> None:
    from PIL import Image
    import cv2
    from scr.services.ultralytics_compat import ensure_cv2_highgui_compat

    def progress(message: str) -> None:
        if progress_callback is not None:
            progress_callback(message)

    ensure_cv2_highgui_compat()
    from ultralytics import YOLO

    mode = config.get("source_mode", "图片文件夹")
    model_path = str(config.get("model_path") or "").strip()
    if not model_path:
        raise ValueError("请选择一个用于检测的模型。")
    if mode in {"图片文件夹", "图片/视频文件夹", "图片/视频"}:
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
        if mode in {"图片文件夹", "图片/视频文件夹", "图片/视频"}:
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
