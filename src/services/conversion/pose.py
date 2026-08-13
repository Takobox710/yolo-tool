from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from src.services.conversion.class_mapping import normalize_class_name_mapping


class PoseValidationError(ValueError):
    """One Labelme image cannot form valid YOLO Pose labels."""


@dataclass(frozen=True)
class PoseConversion:
    lines: list[str]
    keypoint_count: int | None


def build_pose_lines_from_annotations(image_size: tuple[int, int], annotations) -> tuple[list[str], int | None]:
    width, height = map(float, image_size)
    boxes = [(index, item) for index, item in enumerate(annotations) if item.shape in {"rect", "obb", "obb_mirror", "obb_single", "line_expand"}]
    points = [(index, item) for index, item in enumerate(annotations) if item.shape == "point" and item.points]
    if not boxes and not points:
        return [], None
    if not boxes or not points:
        raise PoseValidationError("Pose 标注必须同时包含标注框和关键点")
    grouped = {index: [] for index, _item in boxes}
    for point_index, point_annotation in points:
        point = point_annotation.points[0]
        matches = [box for box_index, box in boxes if box.class_id == point_annotation.class_id and _inside_polygon(point, box.points)]
        if not matches:
            raise PoseValidationError("存在不在同类别标注框内的关键点")
        if len(matches) > 1:
            raise PoseValidationError("存在同时落入多个同类别标注框的关键点")
        target_index = next(index for index, box in boxes if box is matches[0])
        grouped[target_index].append((point_index, point))
    counts = {len(items) for items in grouped.values()}
    if 0 in counts or len(counts) != 1:
        raise PoseValidationError("所有标注框的关键点数量必须一致且大于 0")
    keypoint_count = counts.pop()
    lines = []
    for box_index, box in boxes:
        x_values = [point[0] for point in box.points]
        y_values = [point[1] for point in box.points]
        x1, x2, y1, y2 = min(x_values), max(x_values), min(y_values), max(y_values)
        values = [(x1 + x2) / 2 / width, (y1 + y2) / 2 / height, (x2 - x1) / width, (y2 - y1) / height]
        tokens = [str(box.class_id), *[f"{_clamp(value):.6f}" for value in values]]
        for _point_index, (x_pos, y_pos) in sorted(grouped[box_index], key=lambda item: item[0]):
            tokens.extend((f"{_clamp(x_pos / width):.6f}", f"{_clamp(y_pos / height):.6f}", "2"))
        lines.append(" ".join(tokens))
    return lines, keypoint_count


def validate_pose_yolo_lines(lines: Iterable[str]) -> int | None:
    counts: set[int] = set()
    for line_number, raw_line in enumerate(lines, start=1):
        parts = raw_line.strip().split()
        if not parts:
            continue
        try:
            values = [float(value) for value in parts[1:]]
        except ValueError as exc:
            raise PoseValidationError(f"第 {line_number} 行包含非数值标签") from exc
        if len(values) < 7 or (len(values) - 4) % 3:
            raise PoseValidationError(f"第 {line_number} 行不是有效的 YOLO Pose 标签")
        counts.add((len(values) - 4) // 3)
    if len(counts) > 1:
        raise PoseValidationError("所有 YOLO Pose 标签的关键点数量必须一致")
    return next(iter(counts), None)


def convert_pose_payload(payload: dict, config, missing_labels: dict[str, list[str]], source_name: str) -> PoseConversion:
    width = float(payload.get("imageWidth") or 0)
    height = float(payload.get("imageHeight") or 0)
    if width <= 0 or height <= 0:
        raise PoseValidationError("缺少有效的 imageWidth/imageHeight")

    mapping = normalize_class_name_mapping(config.class_name_mapping or {})
    boxes: list[tuple[int, int, list[tuple[float, float]]]] = []
    points: list[tuple[int, int, tuple[float, float]]] = []
    unsupported: list[str] = []
    for index, shape in enumerate(payload.get("shapes", [])):
        raw_label = str(shape.get("label") or "").strip()
        mapped_name = mapping.get(raw_label, raw_label)
        if mapped_name not in (config.class_names or []):
            missing_labels[raw_label or "unknown"].append(source_name)
            continue
        class_id = config.class_names.index(mapped_name)
        shape_type = str(shape.get("shape_type") or "").strip()
        shape_points = _read_points(shape.get("points", []))
        if shape_type == "point" and len(shape_points) == 1:
            points.append((index, class_id, shape_points[0]))
        elif shape_type == "rectangle" and len(shape_points) >= 2:
            x1, y1 = shape_points[0]
            x2, y2 = shape_points[1]
            boxes.append((index, class_id, [(min(x1, x2), min(y1, y2)), (max(x1, x2), min(y1, y2)), (max(x1, x2), max(y1, y2)), (min(x1, x2), max(y1, y2))]))
        elif shape_type == "oriented_rectangle" and len(shape_points) >= 4:
            boxes.append((index, class_id, shape_points[:4]))
        elif shape_points:
            unsupported.append(raw_label or "unknown")

    if unsupported:
        raise PoseValidationError(f"包含不支持的 Pose 标注形状：{', '.join(sorted(set(unsupported)))}")
    if not boxes and not points:
        return PoseConversion([], None)
    if not boxes:
        raise PoseValidationError("缺少标注框，无法匹配关键点")
    if not points:
        raise PoseValidationError("缺少关键点，无法生成 Pose 标注")

    grouped: dict[int, list[tuple[int, tuple[float, float]]]] = {box[0]: [] for box in boxes}
    for point_index, class_id, point in points:
        matches = [box for box in boxes if box[1] == class_id and _inside_polygon(point, box[2])]
        if not matches:
            raise PoseValidationError(f"第 {point_index + 1} 个关键点不在同类别标注框内")
        if len(matches) > 1:
            raise PoseValidationError(f"第 {point_index + 1} 个关键点同时落入多个同类别标注框")
        grouped[matches[0][0]].append((point_index, point))

    counts = {len(items) for items in grouped.values()}
    if not counts or 0 in counts:
        raise PoseValidationError("每个标注框都必须包含至少一个同类别关键点")
    if len(counts) != 1:
        raise PoseValidationError("所有标注框的关键点数量必须一致")
    keypoint_count = counts.pop()
    expected = config.pose_keypoint_count
    if expected is not None and expected != keypoint_count:
        raise PoseValidationError(f"关键点数量不一致：当前为 {keypoint_count}，数据集要求 {expected}")

    lines: list[str] = []
    for box_index, class_id, polygon in sorted(boxes, key=lambda item: item[0]):
        x_values = [point[0] for point in polygon]
        y_values = [point[1] for point in polygon]
        values = [
            (min(x_values) + max(x_values)) / 2 / width,
            (min(y_values) + max(y_values)) / 2 / height,
            (max(x_values) - min(x_values)) / width,
            (max(y_values) - min(y_values)) / height,
        ]
        tokens = [str(class_id), *[f"{_clamp(value):.6f}" for value in values]]
        for _point_index, (x_pos, y_pos) in sorted(grouped[box_index], key=lambda item: item[0]):
            tokens.extend((f"{_clamp(x_pos / width):.6f}", f"{_clamp(y_pos / height):.6f}", "2"))
        lines.append(" ".join(tokens))
    return PoseConversion(lines, keypoint_count)


def _read_points(raw_points: Iterable) -> list[tuple[float, float]]:
    result: list[tuple[float, float]] = []
    for raw in raw_points:
        if not isinstance(raw, (list, tuple)) or len(raw) < 2:
            continue
        try:
            result.append((float(raw[0]), float(raw[1])))
        except (TypeError, ValueError):
            continue
    return result


def _inside_polygon(point: tuple[float, float], polygon: list[tuple[float, float]]) -> bool:
    if len(polygon) == 4 and len({round(item[0], 6) for item in polygon}) == 2 and len({round(item[1], 6) for item in polygon}) == 2:
        xs = [item[0] for item in polygon]
        ys = [item[1] for item in polygon]
        return min(xs) <= point[0] <= max(xs) and min(ys) <= point[1] <= max(ys)
    px, py = point
    inside = False
    for index, (x1, y1) in enumerate(polygon):
        x2, y2 = polygon[(index + 1) % len(polygon)]
        if _point_on_segment(point, (x1, y1), (x2, y2)):
            return True
        if ((y1 > py) != (y2 > py)) and px <= (x2 - x1) * (py - y1) / ((y2 - y1) or 1e-12) + x1:
            inside = not inside
    return inside


def _point_on_segment(point, start, end) -> bool:
    px, py = point
    x1, y1 = start
    x2, y2 = end
    cross = (px - x1) * (y2 - y1) - (py - y1) * (x2 - x1)
    if abs(cross) > 1e-6:
        return False
    return min(x1, x2) <= px <= max(x1, x2) and min(y1, y2) <= py <= max(y1, y2)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


__all__ = [
    "PoseConversion",
    "PoseValidationError",
    "build_pose_lines_from_annotations",
    "convert_pose_payload",
    "validate_pose_yolo_lines",
]
