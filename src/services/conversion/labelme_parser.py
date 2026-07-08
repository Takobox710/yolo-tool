from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Iterable

from src.services.conversion.class_mapping import normalize_class_name_mapping
from src.services.conversion.types import ConversionConfig


def convert_label_file(
    json_path: Path,
    config: ConversionConfig,
    missing_labels: dict[str, list[str]],
) -> list[str]:
    payload = json.loads(Path(json_path).read_text(encoding="utf-8"))
    width = payload.get("imageWidth")
    height = payload.get("imageHeight")
    if not width or not height:
        raise ValueError(f"{json_path.name} 缺少 imageWidth/imageHeight")

    lines: list[str] = []
    mapping = normalize_class_name_mapping(config.class_name_mapping or {})
    for shape in payload.get("shapes", []):
        raw_label = str(shape.get("label") or "").strip()
        mapped_name = mapping.get(raw_label, raw_label)
        if mapped_name not in config.class_names:
            missing_labels[raw_label or "unknown"].append(Path(json_path).name)
            continue
        class_id = config.class_names.index(mapped_name)
        if config.task_mode == "obb":
            points = shape_to_obb_points(shape, config)
            if points is None:
                missing_labels[f"{raw_label}(unsupported)"].append(Path(json_path).name)
                continue
            coords = normalize_points(points, width, height)
            lines.append(
                f"{class_id} "
                + " ".join(f"{value:.6f}" for pair in coords for value in pair)
            )
            continue
        bbox = shape_to_detect_bbox(shape)
        if bbox is None:
            missing_labels[f"{raw_label}(unsupported)"].append(Path(json_path).name)
            continue
        x_center, y_center, box_width, box_height = bbox
        lines.append(
            f"{class_id} "
            f"{x_center / width:.6f} {y_center / height:.6f} "
            f"{box_width / width:.6f} {box_height / height:.6f}"
        )
    return lines


def shape_to_obb_points(
    shape: dict, config: ConversionConfig
) -> list[tuple[float, float]] | None:
    points = shape.get("points", [])
    shape_type = shape.get("shape_type", "")
    if shape_type == "oriented_rectangle" and len(points) == 4:
        return [(float(x), float(y)) for x, y in points]
    if shape_type == "rectangle" and len(points) == 2:
        (x1, y1), (x2, y2) = points
        return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
    if shape_type == "line" and len(points) == 2 and config.line_to_obb:
        (x1, y1), (x2, y2) = points
        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy)
        if length == 0:
            return None
        nx = -dy / length
        ny = dx / length
        half = config.line_half_width
        return [
            (x1 + nx * half, y1 + ny * half),
            (x2 + nx * half, y2 + ny * half),
            (x2 - nx * half, y2 - ny * half),
            (x1 - nx * half, y1 - ny * half),
        ]
    return None


def shape_to_detect_bbox(shape: dict) -> tuple[float, float, float, float] | None:
    points = shape.get("points", [])
    if len(points) < 2:
        return None
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    x1, x2 = min(xs), max(xs)
    y1, y2 = min(ys), max(ys)
    return ((x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1)


def normalize_points(
    points: Iterable[tuple[float, float]], width: float, height: float
) -> list[tuple[float, float]]:
    return [
        (
            max(0.0, min(1.0, x / width)),
            max(0.0, min(1.0, y / height)),
        )
        for x, y in points
    ]
