from __future__ import annotations

import sys
from pathlib import Path

import yaml

from src.services.training.model_catalog import (
    infer_task_mode_from_config,
    infer_task_mode_from_model,
    read_yaml_mapping,
    select_training_model,
)


def app_cli_command(*args: str) -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, *args]
    return [sys.executable, "-m", "src.main", *args]


def build_train_command(config: dict) -> list[str]:
    model = select_training_model(config)
    task_mode = infer_task_mode_from_config(config)
    command = app_cli_command("--yolo-train", task_mode, "train")
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
        ("optimizer", config.get("optimizer")),
        ("mosaic", config.get("mosaic")),
        ("fliplr", config.get("fliplr")),
        ("flipud", config.get("flipud")),
        ("mixup", config.get("mixup")),
        ("scale", config.get("scale")),
        ("translate", config.get("translate")),
        ("degrees", config.get("degrees")),
        ("hsv_h", config.get("hsv_h", config.get("hsv"))),
        ("hsv_s", config.get("hsv_s")),
        ("hsv_v", config.get("hsv_v")),
    ]
    for key, value in fields:
        if value in (None, ""):
            continue
        command.append(f"{key}={value}")
    return command


def repair_validation_path_if_needed(dataset_yaml: str | Path | None) -> bool:
    path_text = str(dataset_yaml or "").strip()
    if not path_text:
        return False
    data_path = Path(path_text)
    payload = read_yaml_mapping(data_path)
    if not isinstance(payload, dict):
        return False
    train_value = str(payload.get("train") or "").strip()
    val_value = str(payload.get("val") or "").strip()
    if not train_value or not val_value or "\\" not in val_value:
        return False

    train_path = Path(train_value.replace("\\", "/"))
    train_parts = list(train_path.parts)
    replaced = False
    for index, part in enumerate(train_parts):
        if part.lower() == "train":
            train_parts[index] = "val"
            replaced = True
            break
    if not replaced:
        return False

    payload["val"] = str(Path(*train_parts)).replace("\\", "/")
    data_path.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return True


def build_export_command(
    model_path: str, export_format: str, imgsz: int | str = 640
) -> list[str]:
    return app_cli_command(
        "--yolo-export",
        f"model={model_path}",
        f"format={export_format}",
        f"imgsz={imgsz}",
    )


def build_val_command(config: dict) -> list[str]:
    model = str(config.get("model_path") or "").strip()
    task_mode = infer_task_mode_from_model(model)
    command = app_cli_command("--yolo-val", task_mode, "val")
    fields = [
        ("model", model),
        ("data", config.get("data")),
        ("conf", config.get("confidence")),
        ("iou", config.get("iou")),
        ("imgsz", config.get("imgsz")),
        ("project", config.get("save_dir")),
    ]
    for key, value in fields:
        if value in (None, ""):
            continue
        command.append(f"{key}={value}")
    return command
