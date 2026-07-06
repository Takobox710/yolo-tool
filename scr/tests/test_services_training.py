import json

import os

import sys

from pathlib import Path

from types import SimpleNamespace

import pytest

def make_image(path: Path, size=(100, 100), color="white"):
    from PIL import Image

    Image.new("RGB", size, color).save(path)


def test_training_command_and_detection_helpers(tmp_path):
    from scr.services.detection_service import normalize_detection_item, scan_candidate_models
    from scr.services.training_service import build_train_command, infer_task_mode_from_model

    command = build_train_command(
        {"model_yaml": "data/yolov8m-obb.yaml", "data": "data.yaml", "epochs": 800, "lr": 0.001}
    )
    assert command[-2:] != ["obb", "train"]
    assert "--yolo-train" in command
    assert "obb" in command
    assert "train" in command
    assert "pixi" not in command
    assert "model=data/yolov8m-obb.yaml" in command
    assert "lr0=0.001" in command
    assert infer_task_mode_from_model("yolo11n-obb.pt") == "obb"
    assert infer_task_mode_from_model("yolo11n.pt") == "detect"

    train1 = tmp_path / "train"
    train2 = tmp_path / "train-2"
    (train1 / "weights").mkdir(parents=True)
    (train2 / "weights").mkdir(parents=True)
    (train1 / "weights" / "best.pt").write_text("a", encoding="utf-8")
    (train2 / "weights" / "best.pt").write_text("b", encoding="utf-8")
    os.utime(train1, (1, 1))
    os.utime(train2, (2, 2))

    item = normalize_detection_item("weld", 0.9, [(0, 0), (10, 0), (10, 2), (0, 2)])

    assert scan_candidate_models(tmp_path)[0] == train2 / "weights" / "best.pt"
    assert item.center_x == 5
    assert item.height == 2


def test_training_model_helpers_merge_project_and_app_models_with_project_priority(
    tmp_path, monkeypatch
):
    from scr.services import training_service

    project_root = tmp_path / "project"
    app_root = tmp_path / "app"
    (project_root / "data" / "models").mkdir(parents=True)
    (app_root / "data" / "models").mkdir(parents=True)
    (project_root / "data" / "models" / "shared.pt").write_text("project", encoding="utf-8")
    (project_root / "data" / "models" / "project-only.pt").write_text("project", encoding="utf-8")
    (app_root / "data" / "models" / "shared.pt").write_text("app", encoding="utf-8")
    (app_root / "data" / "models" / "app-only.pt").write_text("app", encoding="utf-8")

    monkeypatch.setattr(training_service, "ROOT", app_root)

    names = training_service.find_training_model_names(project_root)
    shared_resolved = training_service.resolve_training_model_reference("shared.pt", project_root)
    app_only_resolved = training_service.resolve_training_model_reference("app-only.pt", project_root)
    missing_resolved = training_service.resolve_training_model_reference("missing.pt", project_root)

    assert names == ["project-only.pt", "shared.pt", "app-only.pt"]
    assert shared_resolved == str((project_root / "data" / "models" / "shared.pt").resolve())
    assert app_only_resolved == str((app_root / "data" / "models" / "app-only.pt").resolve())
    assert missing_resolved == str((project_root / "data" / "models" / "missing.pt").resolve())


def test_training_model_helpers_avoid_duplicate_scan_when_project_is_app_root(tmp_path):
    from scr.services.training_service import find_training_model_names

    models_dir = tmp_path / "data" / "models"
    models_dir.mkdir(parents=True)
    (models_dir / "alpha.pt").write_text("a", encoding="utf-8")

    assert find_training_model_names(tmp_path, tmp_path) == ["alpha.pt"]


def test_training_command_includes_all_hsv_params_when_configured():
    from scr.services.training_service import build_train_command

    command = build_train_command(
        {
            "model_yaml": "data/yolov8m-obb.yaml",
            "data": "data.yaml",
            "hsv_h": 0.015,
            "hsv_s": 0.7,
            "hsv_v": 0.4,
        }
    )

    assert "hsv_h=0.015" in command
    assert "hsv_s=0.7" in command
    assert "hsv_v=0.4" in command


def test_build_val_command_uses_app_cli_val_entry(tmp_path):
    from scr.services.training_service import build_val_command

    command = build_val_command(
        {
            "model_path": str(tmp_path / "data" / "models" / "yolov8m-obb.pt"),
            "data": str(tmp_path / "data.yaml"),
            "confidence": 0.25,
            "iou": 0.45,
            "imgsz": 960,
            "save_dir": str(tmp_path / "result" / "gui_val"),
        }
    )

    assert "--yolo-val" in command
    assert "obb" in command
    assert "val" in command
    assert f"data={tmp_path / 'data.yaml'}" in command
    assert "imgsz=960" in command


def test_repair_validation_path_if_needed_restores_val_from_train(tmp_path):
    from scr.services.training_service import repair_validation_path_if_needed

    dataset_yaml = tmp_path / "data.yaml"
    dataset_yaml.write_text(
        "\n".join(
            [
                "path: .",
                "train: data/train/images",
                r"val: ..\images",
                "test: data/test/images",
                "names: ['weld']",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    changed = repair_validation_path_if_needed(dataset_yaml)

    assert changed is True
    assert "val: data/val/images" in dataset_yaml.read_text(encoding="utf-8")


def test_read_train_metrics_uses_map5095_for_best_checkpoint(tmp_path):
    from scr.services.training_service import read_train_metrics

    run_dir = tmp_path / "result" / "train-3"
    run_dir.mkdir(parents=True)
    (run_dir / "results.csv").write_text(
        "\n".join(
            [
                "epoch,time,metrics/mAP50(B),metrics/mAP50-95(B),val/box_loss,metrics/recall(B)",
                "244,120,0.960,0.610,0.2100,0.880",
                "374,180,0.950,0.640,0.1800,0.900",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    best_metrics = read_train_metrics(run_dir, "best.pt")
    last_metrics = read_train_metrics(run_dir, "last.pt")

    assert best_metrics["epochs"] == 374
    assert best_metrics["map50"] == "95.0%"
    assert best_metrics["map50_95"] == "64.0%"
    assert last_metrics["epochs"] == 374


def test_read_train_metrics_prefers_latest_epoch_when_best_score_ties(tmp_path):
    from scr.services.training_service import read_train_metrics

    run_dir = tmp_path / "result" / "train-4"
    run_dir.mkdir(parents=True)
    (run_dir / "results.csv").write_text(
        "\n".join(
            [
                "epoch,time,metrics/mAP50(B),metrics/mAP50-95(B),val/box_loss,metrics/recall(B)",
                "100,60,0.900,0.500,0.2500,0.800",
                "120,72,0.910,0.500,0.2200,0.820",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    best_metrics = read_train_metrics(run_dir, "best.pt")

    assert best_metrics["epochs"] == 120


def test_training_command_ignores_dataset_yaml_in_model_field(tmp_path):
    from scr.services.training_service import build_train_command

    dataset_yaml = tmp_path / "data.yaml"
    dataset_yaml.write_text(
        "path: data\ntrain: train/images\nval: val/images\nnames: ['weld']\n",
        encoding="utf-8",
    )
    obb_model = tmp_path / "data" / "models" / "yolov8m-obb.pt"
    obb_model.parent.mkdir(parents=True)
    obb_model.write_text("weights", encoding="utf-8")

    command = build_train_command(
        {
            "model_yaml": str(dataset_yaml),
            "base_model": str(obb_model),
            "pretrained": str(obb_model),
            "data": str(dataset_yaml),
        }
    )

    assert "model=" + str(dataset_yaml) not in command
    assert "model=" + str(obb_model) in command
    assert "pretrained=" + str(obb_model) in command
    assert "obb" in command


def test_train_cli_falls_back_to_pretrained_when_model_points_to_dataset_yaml(monkeypatch, tmp_path):
    from scr.train_cli import run_train_cli

    dataset_yaml = tmp_path / "data.yaml"
    dataset_yaml.write_text(
        "path: data\ntrain: train/images\nval: val/images\nnames: ['weld']\n",
        encoding="utf-8",
    )
    obb_model = tmp_path / "data" / "models" / "yolov8m-obb.pt"
    obb_model.parent.mkdir(parents=True)
    obb_model.write_text("weights", encoding="utf-8")
    calls = {}

    class FakeYOLO:
        def __init__(self, model):
            calls["model"] = model

        def train(self, **kwargs):
            calls["kwargs"] = kwargs

    monkeypatch.setitem(
        sys.modules,
        "scr.services.ultralytics_compat",
        SimpleNamespace(ensure_cv2_highgui_compat=lambda: None),
    )
    monkeypatch.setitem(sys.modules, "ultralytics", SimpleNamespace(YOLO=FakeYOLO))

    exit_code = run_train_cli(
        [
            "detect",
            "train",
            f"model={dataset_yaml}",
            f"data={dataset_yaml}",
            f"pretrained={obb_model}",
        ]
    )

    assert exit_code == 0
    assert calls["model"] == str(obb_model)
    assert calls["kwargs"]["task"] == "obb"
    assert calls["kwargs"]["data"] == str(dataset_yaml)
    assert calls["kwargs"]["pretrained"] == str(obb_model)
