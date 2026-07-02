from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from scr.paths import ROOT, RUNTIME_ROOT


APP_STATE_PATH = RUNTIME_ROOT / "app_state.json"


def project_settings_path(project_root: Path = ROOT) -> Path:
    return Path(project_root) / "data" / "runtime" / "settings.json"


def load_last_project_root(app_state_path: Path | None = None, fallback: Path = ROOT) -> Path:
    fallback = Path(fallback)
    app_state_path = Path(app_state_path or APP_STATE_PATH)
    try:
        payload = json.loads(app_state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return fallback
    raw_path = payload.get("last_project_root")
    if not raw_path:
        return fallback
    candidate = Path(raw_path).expanduser()
    if not candidate.exists():
        return fallback
    return candidate.resolve()


def save_last_project_root(
    project_root: Path, app_state_path: Path | None = None
) -> None:
    app_state_path = Path(app_state_path or APP_STATE_PATH)
    app_state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"last_project_root": str(Path(project_root).resolve())}
    app_state_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def build_default_settings(project_root: Path = ROOT) -> dict[str, Any]:
    project_root = Path(project_root)
    data_root = project_root / "data"
    models_root = data_root / "models"
    return {
        "project": {"root": str(project_root)},
        "paths": {
            "images_dir": str(project_root / "images"),
            "annotations_dir": str(project_root / "images"),
            "labels_dir": str(project_root / "labels"),
            "dataset_dir": str(data_root),
            "models_dir": str(models_root),
            "result_dir": str(project_root / "result"),
        },
        "task": {"mode": "detect"},
        "dataset": {
            "class_names": ["weld"],
            "split_ratios": {"train": 0.8, "val": 0.2, "test": 0.0},
            "line_to_obb": {"enabled": True, "half_width": 10.0},
            "random_seed": 42,
        },
        "image_resize": {
            "long_edge": 960,
            "canvas_size": 960,
            "background": "white",
            "output_dir": str(project_root / "images_resized"),
            "backup_dir": str(project_root / "images_backup"),
            "backup_enabled": False,
        },
        "training": {
            "model_yaml": "",
            "base_model": "yolov8s.pt",
            "pretrained": str(models_root / "yolov8s.pt"),
            "data": str(data_root / "data.yaml"),
            "project": str(project_root / "result"),
            "export_format": "onnx",
            "lr": 0.001,
            "epochs": 500,
            "patience": 100,
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
            "hsv_s": 0.7,
            "hsv_v": 0.4,
            "optimizer": "auto",
        },
        "validation": {
            "model_path": "",
            "source_mode": "图片/视频文件夹",
            "source_path": "",
            "camera_index": 0,
            "confidence": 0.25,
            "iou": 0.45,
            "save_dir": str(project_root / "result" / "gui_predict"),
        },
        "conversion": {
            "use_labelme": True,
            "backup_yolo_files": False,
            "class_name_mappings": {},
        },
        "rename": {
            "prefix": "A",
            "start_index": 1,
            "padding": 1,
            "include_labelme": False,
            "include_yolo": False,
        },
        "ui": {"last_page": "home", "window_width": 1100, "window_height": 770},
        "features": {
            "distribution_multi_class_mode": False,
            "custom_command_dialog": True,
            "show_help_icons": True,
            "resize_output_mode": "输出到新文件夹",
        },
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
    def __init__(self, settings_path: Path | None = None, project_root: Path | None = None):
        resolved_root = (
            load_last_project_root() if project_root is None else Path(project_root)
        )
        self.project_root = resolved_root
        self.settings_path = Path(settings_path) if settings_path is not None else project_settings_path(self.project_root)

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
        settings.setdefault("project", {})["root"] = str(self.project_root)
        self.save(settings)
        return settings

    def reset_to_defaults(self) -> dict[str, Any]:
        defaults = build_default_settings(self.project_root)
        self.save(defaults)
        return defaults

    def save(self, data: dict[str, Any]) -> None:
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        save_last_project_root(self.project_root)
