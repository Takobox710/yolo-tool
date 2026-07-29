from __future__ import annotations

from typing import Any

from src.services.training import (
    infer_task_mode_from_config,
    infer_task_mode_from_model,
    select_training_model,
)
from src.bootstrap.cli_common import _parse_key_values

def _run_train_cli_impl(argv: list[str]) -> int:
    if len(argv) < 2:
        raise SystemExit("Usage: --yolo-train <detect|obb|seg> train key=value ...")
    task_mode, command, *items = argv
    if task_mode not in {"detect", "obb", "seg"}:
        raise SystemExit("训练任务类型必须是 detect、obb 或 seg")
    if command != "train":
        raise SystemExit(f"Unsupported training command: {command}")

    from src.services.ultralytics_compat import ensure_cv2_highgui_compat

    ensure_cv2_highgui_compat()
    from ultralytics import YOLO

    options = _parse_key_values(items)
    model_path = select_training_model(options)
    if not model_path:
        raise SystemExit("Missing model=... for training")
    options.pop("model", None)
    inferred_mode = infer_task_mode_from_config(
        {"model": model_path, "pretrained": options.get("pretrained")}
    )
    if task_mode == "detect" and inferred_mode in {"obb", "seg"}:
        task_mode = inferred_mode
    model = YOLO(str(model_path))
    model.train(task=task_mode, **options)
    return 0



def run_train(argv: list[str]) -> int:
    return _run_train_cli_impl(argv)


__all__ = ["run_train"]
