from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PACKAGE_ROOT / "runtime"
DEFAULT_SETTINGS_PATH = RUNTIME_ROOT / "settings.json"


def build_default_settings(project_root: Path = ROOT) -> dict[str, Any]:
    project_root = Path(project_root)
    data_root = project_root / "data"
    return {
        "project": {"root": str(project_root)},
        "paths": {
            "images_dir": str(project_root / "images"),
            "annotations_dir": str(project_root / "images"),
            "labels_dir": str(project_root / "labels"),
            "dataset_dir": str(data_root),
            "result_dir": str(project_root / "result"),
        },
        "task": {"mode": "obb"},
        "dataset": {
            "class_names": ["weld"],
            "split_ratios": {"train": 0.7, "val": 0.2, "test": 0.1},
            "line_to_obb": {"enabled": True, "half_width": 10.0},
            "random_seed": 42,
        },
        "image_resize": {
            "long_edge": 960,
            "canvas_size": 960,
            "background": "white",
            "output_dir": str(project_root / "images_resized"),
            "backup_dir": str(project_root / "images_backup"),
        },
        "training": {
            "model_yaml": str(data_root / "yolov8m-obb.yaml"),
            "base_model": "yolo11n-obb",
            "pretrained": "yolov8m-obb.pt",
            "data": str(data_root / "data.yaml"),
            "project": str(project_root / "result"),
            "export_format": "onnx",
            "lr": 0.001,
            "epochs": 800,
            "patience": 150,
            "workers": 2,
            "batch": 16,
            "imgsz": 640,
            "device": "0",
            "mosaic": 1.0,
            "fliplr": 0.5,
            "flipud": 0.0,
            "mixup": 0.0,
            "scale": 0.5,
            "translate": 0.1,
            "degrees": 0.0,
            "hsv_h": 0.015,
            "optimizer": "auto",
        },
        "validation": {
            "model_path": "",
            "source_mode": "图片文件夹",
            "source_path": "",
            "camera_index": 0,
            "confidence": 0.25,
            "iou": 0.45,
            "save_dir": str(project_root / "result" / "gui_predict"),
        },
        "ui": {"last_page": "home", "window_width": 1100, "window_height": 780},
        "features": {"custom_command_dialog": True},
    }


def deep_merge(defaults: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(defaults)
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


class SettingsService:
    def __init__(self, settings_path: Path = DEFAULT_SETTINGS_PATH, project_root: Path = ROOT):
        self.settings_path = Path(settings_path)
        self.project_root = Path(project_root)

    def load(self) -> dict[str, Any]:
        defaults = build_default_settings(self.project_root)
        if not self.settings_path.exists():
            self.save(defaults)
            return defaults
        try:
            payload = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            payload = {}
        settings = deep_merge(defaults, payload)
        self.save(settings)
        return settings

    def save(self, data: dict[str, Any]) -> None:
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
