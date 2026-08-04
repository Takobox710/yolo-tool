from __future__ import annotations

from src.bootstrap.cli_common import _parse_key_values
from src.services.training import infer_task_mode_from_config

def _run_val_cli_impl(argv: list[str]) -> int:
    if len(argv) < 2:
        raise SystemExit("Usage: --yolo-val <detect|obb|seg> val key=value ...")
    task_mode, command, *items = argv
    if task_mode not in {"detect", "obb", "seg"}:
        raise SystemExit("验证任务类型必须是 detect、obb 或 seg")
    if command != "val":
        raise SystemExit(f"Unsupported validation command: {command}")

    from src.services.ultralytics_compat import ensure_cv2_highgui_compat

    ensure_cv2_highgui_compat()
    from ultralytics import YOLO

    options = _parse_key_values(items)
    model_path = options.pop("model", None)
    if not model_path:
        raise SystemExit("Missing model=... for validation")
    data_path = options.get("data")
    if not data_path:
        raise SystemExit("Missing data=... for validation")
    inferred_mode = infer_task_mode_from_config({"model": model_path})
    if task_mode == "detect" and inferred_mode in {"obb", "seg"}:
        task_mode = inferred_mode
    model = YOLO(str(model_path))
    model.val(task=task_mode, **options)
    return 0
