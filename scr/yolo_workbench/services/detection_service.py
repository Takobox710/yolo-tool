from __future__ import annotations

import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


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
    return target


def run_prediction(config: dict, stop_event, callback: Callable[[dict], None]) -> None:
    from PIL import Image
    import cv2
    from ultralytics import YOLO

    model = YOLO(config["model_path"])
    mode = config.get("source_mode", "图片文件夹")
    save_dir = build_save_dir(Path(config.get("save_dir", "result/gui_predict")))
    if mode in {"图片文件夹", "图片/视频文件夹"}:
        paths = sorted(
            path
            for path in Path(config["source_path"]).iterdir()
            if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".mp4", ".avi", ".mov", ".mkv"}
        )
        total = len(paths)
        image_suffixes = {".jpg", ".jpeg", ".png", ".bmp"}
        for index, image_path in enumerate(paths, start=1):
            if stop_event.is_set():
                break
            if image_path.suffix.lower() not in image_suffixes:
                config = {**config, "source_mode": "视频", "source_path": str(image_path)}
                run_prediction(config, stop_event, callback)
                continue
            start = time.perf_counter()
            result = model.predict(source=str(image_path), conf=config.get("confidence", 0.25), iou=config.get("iou", 0.45), verbose=False)[0]
            elapsed = time.perf_counter() - start
            plotted = result.plot()
            cv2.imwrite(str(save_dir / image_path.name), plotted)
            original = Image.open(image_path).convert("RGB")
            callback(
                {
                    "source_image": original,
                    "result_image": Image.fromarray(cv2.cvtColor(plotted, cv2.COLOR_BGR2RGB)),
                    "items": extract_detection_items(result),
                    "status": f"{index}/{total} {image_path.name}",
                    "elapsed": elapsed,
                }
            )
    else:
        source = int(config.get("camera_index", 0)) if mode == "摄像头" else config.get("source_path")
        cap = cv2.VideoCapture(source)
        frame_index = 0
        try:
            while cap.isOpened() and not stop_event.is_set():
                ok, frame = cap.read()
                if not ok:
                    break
                frame_index += 1
                start = time.perf_counter()
                result = model.predict(source=frame, conf=config.get("confidence", 0.25), iou=config.get("iou", 0.45), verbose=False)[0]
                elapsed = time.perf_counter() - start
                plotted = result.plot()
                callback(
                    {
                        "source_image": Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)),
                        "result_image": Image.fromarray(cv2.cvtColor(plotted, cv2.COLOR_BGR2RGB)),
                        "items": extract_detection_items(result),
                        "status": f"frame {frame_index}",
                        "elapsed": elapsed,
                    }
                )
        finally:
            cap.release()
