from __future__ import annotations

from pathlib import Path


def infer_task_mode_from_model(model_name: str | Path | None) -> str:
    name = Path(str(model_name or "")).name.lower()
    return "obb" if "obb" in name else "detect"


def build_train_command(config: dict) -> list[str]:
    model = config.get("model_yaml") or config.get("base_model") or config.get("model")
    task_mode = infer_task_mode_from_model(model)
    command = ["pixi", "run", "yolo", task_mode, "train"]
    fields = [
        ("model", model),
        ("data", config.get("data")),
        ("epochs", config.get("epochs")),
        ("imgsz", config.get("imgsz")),
        ("batch", config.get("batch")),
        ("workers", config.get("workers")),
        ("patience", config.get("patience")),
        ("project", config.get("project")),
        ("pretrained", config.get("pretrained")),
        ("device", config.get("device")),
        ("lr0", config.get("lr")),
        ("mosaic", config.get("mosaic")),
        ("fliplr", config.get("fliplr")),
        ("flipud", config.get("flipud")),
        ("mixup", config.get("mixup")),
        ("scale", config.get("scale")),
        ("translate", config.get("translate")),
        ("degrees", config.get("degrees")),
    ]
    for key, value in fields:
        if value in (None, ""):
            continue
        command.append(f"{key}={value}")
    return command


def build_export_command(model_path: str, export_format: str, imgsz: int | str = 640) -> list[str]:
    return ["pixi", "run", "yolo", "export", f"model={model_path}", f"format={export_format}", f"imgsz={imgsz}"]


def latest_result_csv(result_dir: Path) -> Path | None:
    candidates = sorted(Path(result_dir).glob("train*/results.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None
