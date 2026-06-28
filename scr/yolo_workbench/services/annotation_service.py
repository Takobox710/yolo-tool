from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw


@dataclass
class Annotation:
    class_id: int
    label: str
    points: list[tuple[float, float]]
    confidence: float | None = None


def load_yolo_annotations(image_size: tuple[int, int], label_path: Path, task_mode: str, class_names: list[str]) -> list[Annotation]:
    width, height = image_size
    annotations: list[Annotation] = []
    if not Path(label_path).exists():
        return annotations
    for raw_line in Path(label_path).read_text(encoding="utf-8").splitlines():
        parts = raw_line.strip().split()
        if not parts:
            continue
        class_id = int(float(parts[0]))
        label = class_names[class_id] if 0 <= class_id < len(class_names) else str(class_id)
        values = [float(item) for item in parts[1:]]
        if task_mode == "obb" and len(values) >= 8:
            points = [(values[i] * width, values[i + 1] * height) for i in range(0, 8, 2)]
        elif task_mode == "detect" and len(values) >= 4:
            cx, cy, bw, bh = values[:4]
            x_center, y_center = cx * width, cy * height
            box_width, box_height = bw * width, bh * height
            x1 = x_center - box_width / 2
            y1 = y_center - box_height / 2
            x2 = x_center + box_width / 2
            y2 = y_center + box_height / 2
            points = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
        else:
            continue
        annotations.append(Annotation(class_id=class_id, label=label, points=points))
    return annotations


def render_annotation_preview(image_path: Path, annotations: list[Annotation]) -> Image.Image:
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    for annotation in annotations:
        points = annotation.points + [annotation.points[0]]
        draw.line(points, fill="#00A3FF", width=3)
        if annotation.points:
            draw.text(annotation.points[0], annotation.label, fill="#00A3FF")
    return image
