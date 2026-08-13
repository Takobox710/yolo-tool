from __future__ import annotations

from pathlib import Path


YOLO_MODES = {"detect", "obb", "seg", "pose"}


def _valid_coordinate_count(path: Path) -> int | None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return None
    for raw_line in lines:
        parts = raw_line.strip().split()
        if len(parts) < 5:
            continue
        try:
            float(parts[0])
            coordinates = [float(value) for value in parts[1:]]
        except ValueError:
            continue
        if _is_pose_coordinates(coordinates):
            return len(coordinates)
        if len(coordinates) == 4:
            return 4
        if len(coordinates) >= 6 and len(coordinates) % 2 == 0:
            return len(coordinates)
    return None


def infer_yolo_file_mode(path: Path) -> str | None:
    path = Path(path)
    coordinate_count = _valid_coordinate_count(path)
    if coordinate_count is None:
        return None
    if coordinate_count == 4:
        return "detect"
    if _pose_coordinate_count(path) is not None:
        return "pose"
    if coordinate_count == 8:
        return "ambiguous"
    return "seg"


def detect_yolo_mode(labels_dir: Path) -> str | None:
    valid_files: list[tuple[Path, int]] = []
    for path in sorted(Path(labels_dir).glob("*.txt"), key=lambda item: item.name.lower()):
        coordinate_count = _valid_coordinate_count(path)
        if coordinate_count is not None:
            valid_files.append((path, coordinate_count))

    if not valid_files:
        return None
    if all(_pose_coordinate_count(path) is not None for path, _count in valid_files):
        return "pose"
    counts = [count for _path, count in valid_files]
    first_count = counts[0]
    if first_count == 4:
        return "detect"
    if first_count != 8:
        return "seg"
    if len(counts) == 1:
        return "seg"
    if len(counts) == 2:
        return "obb" if all(count == 8 for count in counts) else "seg"
    return "obb" if all(count == 8 for count in counts[:3]) else "seg"


def yolo_file_has_content(path: Path) -> bool:
    return _valid_coordinate_count(Path(path)) is not None


def _is_pose_coordinates(coordinates: list[float]) -> bool:
    return (
        len(coordinates) >= 7
        and (len(coordinates) - 4) % 3 == 0
        and all(value in {0.0, 1.0, 2.0} for value in coordinates[6::3])
    )


def _pose_coordinate_count(path: Path) -> int | None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return None
    for raw_line in lines:
        parts = raw_line.strip().split()
        if len(parts) < 8:
            continue
        try:
            coordinates = [float(value) for value in parts[1:]]
        except ValueError:
            continue
        if _is_pose_coordinates(coordinates):
            return len(coordinates)
    return None


__all__ = [
    "YOLO_MODES",
    "detect_yolo_mode",
    "infer_yolo_file_mode",
    "yolo_file_has_content",
]
