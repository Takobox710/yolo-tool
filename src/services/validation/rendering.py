from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any


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


def normalize_detection_item(
    label: str, confidence: float, points: list[tuple[float, float]]
) -> DetectionItem:
    center_x = sum(point[0] for point in points) / len(points)
    center_y = sum(point[1] for point in points) / len(points)
    width = math.dist(points[0], points[1]) if len(points) >= 2 else 0.0
    height = math.dist(points[1], points[2]) if len(points) >= 3 else 0.0
    angle = (
        math.degrees(
            math.atan2(
                points[1][1] - points[0][1], points[1][0] - points[0][0]
            )
        )
        if len(points) >= 2
        else 0.0
    )
    return DetectionItem(
        label, confidence, center_x, center_y, width, height, angle, points
    )


def extract_detection_items(result: Any) -> list[DetectionItem]:
    names = getattr(result, "names", {})
    obb = getattr(result, "obb", None)
    if obb is not None and getattr(obb, "xyxyxyxy", None) is not None:
        points_list = obb.xyxyxyxy.cpu().tolist()
        confidences = (
            obb.conf.cpu().tolist()
            if getattr(obb, "conf", None) is not None
            else [0.0] * len(points_list)
        )
        classes = (
            obb.cls.cpu().tolist()
            if getattr(obb, "cls", None) is not None
            else [0] * len(points_list)
        )
        return [
            normalize_detection_item(
                names.get(int(class_id), str(int(class_id))),
                float(confidence),
                [(float(x), float(y)) for x, y in points],
            )
            for points, confidence, class_id in zip(
                points_list, confidences, classes
            )
        ]

    boxes = getattr(result, "boxes", None)
    if boxes is None or getattr(boxes, "xyxy", None) is None:
        return []
    xyxy = boxes.xyxy.cpu().tolist()
    confidences = (
        boxes.conf.cpu().tolist()
        if getattr(boxes, "conf", None) is not None
        else [0.0] * len(xyxy)
    )
    classes = (
        boxes.cls.cpu().tolist()
        if getattr(boxes, "cls", None) is not None
        else [0] * len(xyxy)
    )
    items: list[DetectionItem] = []
    for box, confidence, class_id in zip(xyxy, confidences, classes):
        x1, y1, x2, y2 = [float(value) for value in box]
        points = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
        items.append(
            normalize_detection_item(
                names.get(int(class_id), str(int(class_id))),
                float(confidence),
                points,
            )
        )
    return items


def build_save_dir(base_dir: Path, *, create_labels: bool = True) -> Path:
    import time

    target = Path(base_dir) / time.strftime("%Y%m%d_%H%M%S")
    target.mkdir(parents=True, exist_ok=True)
    if create_labels:
        (target / "labels").mkdir(parents=True, exist_ok=True)
    return target


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
        "\n".join(lines) + ("\n" if lines else ""), encoding="utf-8"
    )


def render_result_image_from_frame(result: Any, frame) -> Any:
    from PIL import Image
    import cv2

    plotted = result.plot(img=frame.copy())
    return Image.fromarray(cv2.cvtColor(plotted, cv2.COLOR_BGR2RGB))


def _normalize_point(value: float, size: int) -> float:
    return 0.0 if size <= 0 else value / float(size)
