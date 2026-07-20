from __future__ import annotations

from pathlib import Path
from typing import Any

from src.shared.paths import ROOT


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
            "data": str(data_root / "data.yaml"),
            "source_scope": "全部图片",
            "camera_index": 0,
            "confidence": 0.25,
            "iou": 0.45,
            "imgsz": 640,
            "save_dir": str(project_root / "result" / "gui_val"),
        },
        "conversion": {
            "use_labelme": True,
            "backup_yolo_files": False,
            "class_name_mappings": {},
        },
        "annotation": {
            "auto_save": True,
            "auto_convert_yolo": False,
            "show_yolo_save_in_context_menu": False,
            "show_annotation_names": False,
            "show_canvas_status": True,
            "continuous_draw": False,
            "quick_draw": True,
            "line_expand_enabled": False,
            "line_expand_pixels": 10,
            "ai_prelabel": {
                "model_path": "",
                "confidence": 0.50,
                "iou": 0.45,
                "range_mode": "当前图片",
                "process_mode": "追加",
                "custom_selected_images": [],
            },
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
            "show_last_training_models": False,
            "resize_output_mode": "输出到新文件夹",
        },
    }
