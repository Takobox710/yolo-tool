from __future__ import annotations

from pathlib import Path

from src.services.annotation.annotation_models import EditableAnnotation
from src.services.annotation.circle_geometry import circle_bounds, circle_polygon
from src.services.annotation.geometry import points_to_min_area_obb


def load_editable_annotations(image_size: tuple[int, int], label_path: Path, task_mode: str | None = None) -> list[EditableAnnotation]:
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
        if task_mode == "seg":
            if len(values) < 6 or len(values) % 2:
                continue
            points = [(values[index] * width, values[index + 1] * height) for index in range(0, len(values), 2)]
            annotations.append(EditableAnnotation(class_id, "polygon", points))
        elif len(values) >= 8:
            points = [(values[index] * width, values[index + 1] * height) for index in range(0, 8, 2)]
            annotations.append(EditableAnnotation(class_id, "obb", points))
        elif len(values) >= 4:
            cx, cy, box_w, box_h = values[:4]
            x_center = cx * width
            y_center = cy * height
            half_w = box_w * width / 2
            half_h = box_h * height / 2
            points = [(x_center - half_w, y_center - half_h), (x_center + half_w, y_center - half_h), (x_center + half_w, y_center + half_h), (x_center - half_w, y_center + half_h)]
            annotations.append(EditableAnnotation(class_id, "rect", points))
    return annotations


def annotation_to_seg_points(annotation: EditableAnnotation) -> list[tuple[float, float]]:
    if annotation.shape == "circle":
        x1, y1, x2, y2 = circle_bounds(annotation.points)
        center = ((x1 + x2) / 2, (y1 + y2) / 2)
        radius = max(abs(x2 - x1), abs(y2 - y1)) / 2
        edge = annotation.radius_point or (center[0] + radius, center[1])
        return circle_polygon([center, edge])
    return list(annotation.points)


def save_editable_annotations(image_size: tuple[int, int], label_path: Path, annotations: list[EditableAnnotation], output_mode: str) -> None:
    width, height = image_size
    label_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for annotation in annotations:
        if output_mode == "seg":
            points = annotation_to_seg_points(annotation)
            if len(points) < 3:
                continue
            values: list[float] = []
            for x_pos, y_pos in points:
                values.extend([max(0.0, min(1.0, x_pos / width)), max(0.0, min(1.0, y_pos / height))])
            lines.append(f"{annotation.class_id} " + " ".join(f"{value:.6f}" for value in values))
        elif output_mode == "obb":
            points = annotation.points[:4]
            if annotation.shape == "polygon" or len(annotation.points) != 4:
                points = points_to_min_area_obb(annotation.points)
            values: list[float] = []
            for x_pos, y_pos in points:
                values.extend([max(0.0, min(1.0, x_pos / width)), max(0.0, min(1.0, y_pos / height))])
            lines.append(f"{annotation.class_id} " + " ".join(f"{value:.6f}" for value in values))
        else:
            x1, y1, x2, y2 = circle_bounds(annotation.points) if annotation.shape == "circle" else _detect_points_to_rect(annotation.points)
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
            lines.append(f"{annotation.class_id} {cx:.6f} {cy:.6f} {box_w / width:.6f} {box_h / height:.6f}")
    if lines:
        label_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    elif label_path.exists():
        label_path.write_text("", encoding="utf-8")


def _detect_points_to_rect(points: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


__all__ = ["annotation_to_seg_points", "load_editable_annotations", "save_editable_annotations"]
