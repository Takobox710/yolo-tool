from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


@dataclass
class Annotation:
    class_id: int
    label: str
    points: list[tuple[float, float]]
    confidence: float | None = None


def _infer_annotation_mode(values: list[float], fallback_mode: str) -> str:
    if len(values) >= 8:
        return "obb"
    if len(values) >= 4:
        return "detect"
    return fallback_mode


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
        active_mode = _infer_annotation_mode(values, task_mode)
        if active_mode == "obb" and len(values) >= 8:
            points = [(values[i] * width, values[i + 1] * height) for i in range(0, 8, 2)]
        elif active_mode == "detect" and len(values) >= 4:
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


def _yolo_color(class_id: int) -> tuple[int, int, int]:
    palette = [
        (255, 56, 56),
        (255, 157, 151),
        (255, 112, 31),
        (255, 178, 29),
        (207, 210, 49),
        (72, 249, 10),
        (146, 204, 23),
        (61, 219, 134),
        (26, 147, 52),
        (0, 212, 187),
        (44, 153, 168),
        (0, 194, 255),
        (52, 69, 147),
        (100, 115, 255),
        (0, 24, 236),
        (132, 56, 255),
        (82, 0, 133),
        (203, 56, 255),
        (255, 149, 200),
        (255, 55, 199),
    ]
    return palette[class_id % len(palette)]


def _label_anchor(points: list[tuple[float, float]]) -> tuple[float, float]:
    if not points:
        return 0.0, 0.0
    anchor_x, anchor_y = min(points, key=lambda point: (point[1], point[0]))
    return anchor_x, anchor_y


def _preview_font(image_size: tuple[int, int]) -> ImageFont.ImageFont:
    font_size = max(12, round(min(image_size) / 28))
    for candidate in (
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
    ):
        try:
            return ImageFont.truetype(candidate, font_size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_annotation_preview(image_path: Path, annotations: list[Annotation]) -> Image.Image:
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    font = _preview_font(image.size)
    line_width = max(2, round(min(image.size) / 180))
    for annotation in annotations:
        color = _yolo_color(annotation.class_id)
        points = annotation.points + [annotation.points[0]]
        draw.line(points, fill=color, width=line_width)
        if annotation.points:
            caption = annotation.label
            if annotation.confidence is not None:
                caption = f"{caption} {annotation.confidence:.2f}"
            text_left, text_top = _label_anchor(annotation.points)
            text_bbox = draw.textbbox((0, 0), caption, font=font)
            text_offset_x = text_bbox[0]
            text_offset_y = text_bbox[1]
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            padding_x = 6
            padding_y = 3
            box_left = max(0, int(text_left))
            box_top = max(0, int(text_top - text_height - padding_y * 2))
            box_right = min(image.size[0], box_left + text_width + padding_x * 2)
            box_bottom = min(image.size[1], box_top + text_height + padding_y * 2)
            if box_right - box_left < text_width + padding_x * 2:
                box_left = max(0, image.size[0] - (text_width + padding_x * 2))
                box_right = min(image.size[0], box_left + text_width + padding_x * 2)
            if box_bottom <= box_top:
                box_top = max(0, int(text_top))
                box_bottom = min(image.size[1], box_top + text_height + padding_y * 2)
            draw.rectangle(
                [(box_left, box_top), (box_right, box_bottom)],
                fill=color,
            )
            draw.text(
                (
                    box_left + padding_x - text_offset_x,
                    box_top + padding_y - text_offset_y,
                ),
                caption,
                fill=(255, 255, 255),
                font=font,
            )
    return image
