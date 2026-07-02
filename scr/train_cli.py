from __future__ import annotations

from typing import Any


def _parse_value(raw: str) -> Any:
    text = str(raw)
    lower = text.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    try:
        if "." not in text:
            return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def _parse_key_values(parts: list[str]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for part in parts:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        if key:
            values[key] = _parse_value(value)
    return values


def run_train_cli(argv: list[str]) -> int:
    if len(argv) < 2:
        raise SystemExit("Usage: --yolo-train <detect|obb> train key=value ...")
    task_mode, command, *items = argv
    if command != "train":
        raise SystemExit(f"Unsupported training command: {command}")

    from scr.services.ultralytics_compat import ensure_cv2_highgui_compat

    ensure_cv2_highgui_compat()
    from ultralytics import YOLO

    options = _parse_key_values(items)
    model_path = options.pop("model", None)
    if not model_path:
        raise SystemExit("Missing model=... for training")
    model = YOLO(str(model_path))
    model.train(task=task_mode, **options)
    return 0


def run_export_cli(argv: list[str]) -> int:
    from scr.services.ultralytics_compat import ensure_cv2_highgui_compat

    ensure_cv2_highgui_compat()
    from ultralytics import YOLO

    options = _parse_key_values(argv)
    model_path = options.pop("model", None)
    if not model_path:
        raise SystemExit("Missing model=... for export")
    model = YOLO(str(model_path))
    model.export(**options)
    return 0
