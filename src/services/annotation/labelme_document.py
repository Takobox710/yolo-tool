from __future__ import annotations

import json
from pathlib import Path

from src.services.annotation.annotation_models import EditableAnnotation
from src.services.annotation.geometry import detect_points_to_rect, line_points_to_obb


def _labelme_class_id(label: str, class_names: list[str]) -> int:
    text = str(label or "").strip() or "目标名称"
    if text in class_names:
        return class_names.index(text)
    class_names.append(text)
    return len(class_names) - 1


def load_labelme_annotations(image_size: tuple[int, int], json_path: Path, class_names: list[str], line_expand_pixels: int = 10) -> tuple[list[EditableAnnotation], list[str]]:
    annotations: list[EditableAnnotation] = []
    names = list(class_names)
    if not json_path.exists():
        return annotations, names
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return annotations, names
    for shape in payload.get("shapes", []):
        points: list[tuple[float, float]] = []
        for point in shape.get("points", []):
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
            annotations.append(EditableAnnotation(class_id, "rect", [(left, top), (right, top), (right, bottom), (left, bottom)]))
        elif shape_type == "circle" and len(points) >= 2:
            center, edge = points[:2]
            radius = ((edge[0] - center[0]) ** 2 + (edge[1] - center[1]) ** 2) ** 0.5
            annotations.append(EditableAnnotation(class_id, "circle", [(center[0] - radius, center[1] - radius), (center[0] + radius, center[1] - radius), (center[0] + radius, center[1] + radius), (center[0] - radius, center[1] + radius)], radius_point=edge))
        elif shape_type == "line":
            obb_points = line_points_to_obb(points[:2], float(line_expand_pixels))
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
            left, top, right, bottom = detect_points_to_rect(points)
            annotations.append(EditableAnnotation(class_id, "rect", [(left, top), (right, top), (right, bottom), (left, bottom)]))
    return annotations, names


def save_labelme_annotations(image_size: tuple[int, int], json_path: Path, image_path: Path, annotations: list[EditableAnnotation], class_names: list[str]) -> None:
    width, height = image_size
    shapes: list[dict] = []
    for annotation in annotations:
        label = class_names[annotation.class_id] if 0 <= annotation.class_id < len(class_names) else str(annotation.class_id)
        points = annotation.points
        shape_type = "polygon"
        labelme_points = [[float(x_pos), float(y_pos)] for x_pos, y_pos in points]
        if annotation.shape == "rect":
            x1, y1, x2, y2 = detect_points_to_rect(points)
            shape_type = "rectangle"
            labelme_points = [[float(x1), float(y1)], [float(x2), float(y2)]]
        elif annotation.shape == "circle":
            x1, y1, x2, y2 = detect_points_to_rect(points)
            center = ((x1 + x2) / 2, (y1 + y2) / 2)
            radius = max(abs(x2 - x1), abs(y2 - y1)) / 2
            radius_point = annotation.radius_point or (center[0] + radius, center[1])
            shape_type = "circle"
            labelme_points = [[float(center[0]), float(center[1])], [float(radius_point[0]), float(radius_point[1])]]
        elif annotation.shape in {"obb", "obb_mirror", "obb_single", "line_expand"}:
            shape_type = "oriented_rectangle"
            labelme_points = [[float(x_pos), float(y_pos)] for x_pos, y_pos in points[:4]]
        flags = {}
        if annotation.shape in {"obb", "obb_mirror", "obb_single", "line_expand"}:
            flags["yolo_tool_shape"] = "obb_mirror" if annotation.shape == "line_expand" else annotation.shape
        shapes.append({"label": label, "points": labelme_points, "group_id": None, "description": "", "shape_type": shape_type, "flags": flags, "mask": None})
    payload = {"version": "5.5.0", "flags": {}, "shapes": shapes, "imagePath": image_path.name, "imageData": None, "imageHeight": int(height), "imageWidth": int(width)}
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


__all__ = ["load_labelme_annotations", "save_labelme_annotations"]
