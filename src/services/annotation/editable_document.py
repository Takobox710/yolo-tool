from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from src.services.annotation.circle_geometry import circle_bounds


@dataclass
class EditableAnnotation:
    class_id: int
    shape: str
    points: list[tuple[float, float]]
    radius_point: tuple[float, float] | None = None


def _detect_points_to_rect(points: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def load_editable_annotations(
    image_size: tuple[int, int], label_path: Path
) -> list[EditableAnnotation]:
    width, height = image_size
    annotations: list[EditableAnnotation] = []
    if not label_path.exists():
        return annotations
    for raw_line in label_path.read_text(encoding="utf-8").splitlines():
        parts = raw_line.strip().split()
        if len(parts) < 5:
            continue
        try:
            class_id = int(float(parts[0]))
            values = [float(item) for item in parts[1:]]
        except ValueError:
            continue
        if len(values) >= 8:
            points = [
                (values[index] * width, values[index + 1] * height)
                for index in range(0, 8, 2)
            ]
            annotations.append(EditableAnnotation(class_id, "obb", points))
        elif len(values) >= 4:
            cx, cy, box_w, box_h = values[:4]
            x_center = cx * width
            y_center = cy * height
            half_w = box_w * width / 2
            half_h = box_h * height / 2
            points = [
                (x_center - half_w, y_center - half_h),
                (x_center + half_w, y_center - half_h),
                (x_center + half_w, y_center + half_h),
                (x_center - half_w, y_center + half_h),
            ]
            annotations.append(EditableAnnotation(class_id, "rect", points))
    return annotations


def _labelme_class_id(label: str, class_names: list[str]) -> int:
    text = str(label or "").strip()
    if not text:
        text = "目标名称"
    if text in class_names:
        return class_names.index(text)
    class_names.append(text)
    return len(class_names) - 1


def _line_points_to_obb(
    points: list[tuple[float, float]], half_width: float
) -> list[tuple[float, float]] | None:
    if len(points) != 2:
        return None
    (x1, y1), (x2, y2) = points
    dx = x2 - x1
    dy = y2 - y1
    length = (dx * dx + dy * dy) ** 0.5
    if length < 1:
        return None
    nx = -dy / length
    ny = dx / length
    return [
        (x1 + nx * half_width, y1 + ny * half_width),
        (x2 + nx * half_width, y2 + ny * half_width),
        (x2 - nx * half_width, y2 - ny * half_width),
        (x1 - nx * half_width, y1 - ny * half_width),
    ]


def load_labelme_annotations(
    image_size: tuple[int, int],
    json_path: Path,
    class_names: list[str],
    line_expand_pixels: int = 10,
) -> tuple[list[EditableAnnotation], list[str]]:
    annotations: list[EditableAnnotation] = []
    names = list(class_names)
    if not json_path.exists():
        return annotations, names
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return annotations, names
    for shape in payload.get("shapes", []):
        raw_points = shape.get("points", [])
        points: list[tuple[float, float]] = []
        for point in raw_points:
            if not isinstance(point, (list, tuple)) or len(point) < 2:
                continue
            try:
                points.append((float(point[0]), float(point[1])))
            except (TypeError, ValueError):
                continue
        if not points:
            continue
        class_id = _labelme_class_id(str(shape.get("label") or ""), names)
        shape_type = str(shape.get("shape_type") or "").strip()
        if shape_type == "rectangle" and len(points) >= 2:
            (x1, y1), (x2, y2) = points[:2]
            left, right = sorted((x1, x2))
            top, bottom = sorted((y1, y2))
            annotations.append(
                EditableAnnotation(
                    class_id,
                    "rect",
                    [(left, top), (right, top), (right, bottom), (left, bottom)],
                )
            )
        elif shape_type == "circle" and len(points) >= 2:
            center = points[0]
            edge = points[1]
            radius = ((edge[0] - center[0]) ** 2 + (edge[1] - center[1]) ** 2) ** 0.5
            annotations.append(
                EditableAnnotation(
                    class_id,
                    "circle",
                    [
                        (center[0] - radius, center[1] - radius),
                        (center[0] + radius, center[1] - radius),
                        (center[0] + radius, center[1] + radius),
                        (center[0] - radius, center[1] + radius),
                    ],
                    radius_point=edge,
                )
            )
        elif shape_type == "line":
            obb_points = _line_points_to_obb(points[:2], float(line_expand_pixels))
            if obb_points is not None:
                annotations.append(EditableAnnotation(class_id, "obb_mirror", obb_points))
        elif shape_type == "oriented_rectangle" and len(points) >= 4:
            flags = shape.get("flags") or {}
            stored_shape = str(flags.get("yolo_tool_shape") or "") if isinstance(flags, dict) else ""
            shape_name = stored_shape if stored_shape in {"obb", "obb_mirror", "obb_single"} else "obb"
            annotations.append(EditableAnnotation(class_id, shape_name, points[:4]))
        elif shape_type == "polygon" and len(points) >= 3:
            annotations.append(EditableAnnotation(class_id, "polygon", points))
        elif len(points) >= 4:
            annotations.append(EditableAnnotation(class_id, "polygon", points))
        elif len(points) >= 2:
            left, top, right, bottom = _detect_points_to_rect(points)
            annotations.append(
                EditableAnnotation(
                    class_id,
                    "rect",
                    [(left, top), (right, top), (right, bottom), (left, bottom)],
                )
            )
    return annotations, names


def save_labelme_annotations(
    image_size: tuple[int, int],
    json_path: Path,
    image_path: Path,
    annotations: list[EditableAnnotation],
    class_names: list[str],
) -> None:
    width, height = image_size
    shapes: list[dict] = []
    for annotation in annotations:
        label = (
            class_names[annotation.class_id]
            if 0 <= annotation.class_id < len(class_names)
            else str(annotation.class_id)
        )
        points = annotation.points
        shape_type = "polygon"
        labelme_points = [[float(x_pos), float(y_pos)] for x_pos, y_pos in points]
        if annotation.shape == "rect":
            x1, y1, x2, y2 = _detect_points_to_rect(points)
            shape_type = "rectangle"
            labelme_points = [[float(x1), float(y1)], [float(x2), float(y2)]]
        elif annotation.shape == "circle":
            x1, y1, x2, y2 = _detect_points_to_rect(points)
            center = ((x1 + x2) / 2, (y1 + y2) / 2)
            radius = max(abs(x2 - x1), abs(y2 - y1)) / 2
            radius_point = annotation.radius_point or (center[0] + radius, center[1])
            shape_type = "circle"
            labelme_points = [
                [float(center[0]), float(center[1])],
                [float(radius_point[0]), float(radius_point[1])],
            ]
        elif annotation.shape in {"obb", "obb_mirror", "obb_single", "line_expand"}:
            shape_type = "oriented_rectangle"
            labelme_points = [
                [float(x_pos), float(y_pos)] for x_pos, y_pos in points[:4]
            ]
        flags = {}
        if annotation.shape in {"obb", "obb_mirror", "obb_single", "line_expand"}:
            flags["yolo_tool_shape"] = "obb_mirror" if annotation.shape == "line_expand" else annotation.shape
        shapes.append(
            {
                "label": label,
                "points": labelme_points,
                "group_id": None,
                "description": "",
                "shape_type": shape_type,
                "flags": flags,
                "mask": None,
            }
        )

    payload = {
        "version": "5.5.0",
        "flags": {},
        "shapes": shapes,
        "imagePath": image_path.name,
        "imageData": None,
        "imageHeight": int(height),
        "imageWidth": int(width),
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def save_editable_annotations(
    image_size: tuple[int, int],
    label_path: Path,
    annotations: list[EditableAnnotation],
    output_mode: str,
) -> None:
    width, height = image_size
    label_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for annotation in annotations:
        if output_mode == "obb":
            values: list[float] = []
            points = annotation.points[:4]
            if annotation.shape == "polygon" or len(annotation.points) != 4:
                left, top, right, bottom = _detect_points_to_rect(annotation.points)
                points = [(left, top), (right, top), (right, bottom), (left, bottom)]
            for x_pos, y_pos in points:
                values.extend(
                    [
                        max(0.0, min(1.0, x_pos / width)),
                        max(0.0, min(1.0, y_pos / height)),
                    ]
                )
            lines.append(
                f"{annotation.class_id} "
                + " ".join(f"{value:.6f}" for value in values)
            )
        else:
            if annotation.shape == "circle":
                x1, y1, x2, y2 = circle_bounds(annotation.points)
            else:
                x1, y1, x2, y2 = _detect_points_to_rect(annotation.points)
            x1 = max(0.0, min(float(width), x1))
            x2 = max(0.0, min(float(width), x2))
            y1 = max(0.0, min(float(height), y1))
            y2 = max(0.0, min(float(height), y2))
            box_w = abs(x2 - x1)
            box_h = abs(y2 - y1)
            if box_w < 1 or box_h < 1:
                continue
            cx = (min(x1, x2) + box_w / 2) / width
            cy = (min(y1, y2) + box_h / 2) / height
            lines.append(
                f"{annotation.class_id} {cx:.6f} {cy:.6f} "
                f"{box_w / width:.6f} {box_h / height:.6f}"
            )
    if lines:
        label_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    elif label_path.exists():
        label_path.write_text("", encoding="utf-8")


__all__ = [
    "EditableAnnotation",
    "_detect_points_to_rect",
    "load_editable_annotations",
    "load_labelme_annotations",
    "save_labelme_annotations",
    "save_editable_annotations",
]
