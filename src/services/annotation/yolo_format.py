from __future__ import annotations

from pathlib import Path


YOLO_MODES = {"detect", "obb", "seg"}


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
        if len(coordinates) == 4:
            return 4
        if len(coordinates) >= 6 and len(coordinates) % 2 == 0:
            return len(coordinates)
    return None


def infer_yolo_file_mode(path: Path) -> str | None:
    coordinate_count = _valid_coordinate_count(Path(path))
    if coordinate_count is None:
        return None
    if coordinate_count == 4:
        return "detect"
    if coordinate_count == 8:
        return "ambiguous"
    return "seg"


def detect_yolo_mode(labels_dir: Path) -> str | None:
    valid_files: list[int] = []
    for path in sorted(Path(labels_dir).glob("*.txt"), key=lambda item: item.name.lower()):
        coordinate_count = _valid_coordinate_count(path)
        if coordinate_count is not None:
            valid_files.append(coordinate_count)

    if not valid_files:
        return None
    first_count = valid_files[0]
    if first_count == 4:
        return "detect"
    if first_count != 8:
        return "seg"
    if len(valid_files) == 1:
        return "seg"
    if len(valid_files) == 2:
        return "obb" if all(count == 8 for count in valid_files) else "seg"
    return "obb" if all(count == 8 for count in valid_files[:3]) else "seg"


def yolo_file_has_content(path: Path) -> bool:
    return _valid_coordinate_count(Path(path)) is not None


__all__ = [
    "YOLO_MODES",
    "detect_yolo_mode",
    "infer_yolo_file_mode",
    "yolo_file_has_content",
]
