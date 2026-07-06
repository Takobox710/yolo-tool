import json

import os

import sys

from pathlib import Path

from types import SimpleNamespace

import pytest

def make_image(path: Path, size=(100, 100), color="white"):
    from PIL import Image

    Image.new("RGB", size, color).save(path)


def test_settings_service_loads_and_merges_defaults(tmp_path):
    from scr.services.settings_service import SettingsService

    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps({"training": {"epochs": 12}}, ensure_ascii=False), encoding="utf-8")

    settings = SettingsService(settings_path=settings_path, project_root=tmp_path).load()

    assert settings["project"]["root"] == str(tmp_path)
    assert settings["training"]["epochs"] == 12
    assert settings["training"]["batch"] == 16
    assert settings["image_resize"]["canvas_size"] == 960
    assert settings["features"]["show_help_icons"] is True
    assert settings["features"]["show_last_training_models"] is False
    assert settings["task"]["mode"] == "detect"
    assert settings["dataset"]["split_ratios"] == {"train": 0.8, "val": 0.2, "test": 0.0}
    assert settings["training"]["model_yaml"] == ""
    assert settings["training"]["base_model"] == "yolov8s.pt"
    assert Path(settings["training"]["pretrained"]).name == "yolov8s.pt"
    assert settings["training"]["patience"] == 100
    assert settings["annotation"]["auto_save"] is True
    assert settings["annotation"]["auto_convert_yolo"] is False


def test_settings_service_defaults_to_project_data_runtime(tmp_path):
    from scr.services.settings_service import SettingsService, project_settings_path

    service = SettingsService(project_root=tmp_path)
    settings = service.load()

    assert service.settings_path == tmp_path / "data" / "runtime" / "settings.json"
    assert project_settings_path(tmp_path) == service.settings_path
    assert service.settings_path.exists()
    assert settings["project"]["root"] == str(tmp_path)
    saved = json.loads(service.settings_path.read_text(encoding="utf-8"))
    assert saved["project"]["root"] == "."
    assert saved["paths"]["images_dir"] == "images"
    assert saved["paths"]["dataset_dir"] == "data"
    assert saved["paths"]["models_dir"] == str(Path("data") / "models")
    assert saved["training"]["data"] == str(Path("data") / "data.yaml")
    assert saved["training"]["project"] == "result"
    assert saved["validation"]["save_dir"] == str(Path("result") / "gui_val")


def test_settings_service_keeps_selected_project_root_when_file_has_stale_root(tmp_path):
    from scr.services.settings_service import SettingsService

    stale_root = tmp_path / "old"
    project_root = tmp_path / "current"
    settings_path = project_root / "data" / "runtime" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps(
            {
                "project": {"root": str(stale_root)},
                "training": {"epochs": 33},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    settings = SettingsService(project_root=project_root).load()

    assert settings["project"]["root"] == str(project_root)
    assert settings["training"]["epochs"] == 33


def test_settings_service_can_reset_current_project_to_defaults(tmp_path):
    from scr.services.settings_service import SettingsService, build_default_settings

    project_root = tmp_path / "project-reset"
    settings_path = project_root / "data" / "runtime" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps(
            {
                "training": {"epochs": 12},
                "rename": {"prefix": "custom"},
                "features": {"show_help_icons": False},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    service = SettingsService(project_root=project_root)
    settings = service.reset_to_defaults()
    defaults = build_default_settings(project_root)
    persisted = json.loads(settings_path.read_text(encoding="utf-8"))

    assert settings == defaults
    assert persisted["project"]["root"] == "."
    assert persisted["paths"]["result_dir"] == "result"
    assert persisted["training"]["pretrained"] == "data\\models\\yolov8s.pt"


def test_settings_service_reads_relative_project_paths_as_absolute_runtime_paths(tmp_path):
    from scr.services.settings_service import SettingsService

    project_root = tmp_path / "portable-project"
    settings_path = project_root / "data" / "runtime" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps(
            {
                "project": {"root": "."},
                "paths": {
                    "images_dir": "images",
                    "dataset_dir": "data",
                    "models_dir": "data/models",
                    "result_dir": "result",
                },
                "training": {
                    "data": "data/data.yaml",
                    "project": "result",
                    "pretrained": "data/models/yolov8s.pt",
                },
                "validation": {
                    "save_dir": "result/gui_val",
                    "source_path": "images/demo.jpg",
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    settings = SettingsService(project_root=project_root).load()

    assert settings["project"]["root"] == str(project_root)
    assert settings["paths"]["images_dir"] == str((project_root / "images").resolve())
    assert settings["paths"]["models_dir"] == str((project_root / "data" / "models").resolve())
    assert settings["training"]["data"] == str((project_root / "data" / "data.yaml").resolve())
    assert settings["training"]["pretrained"] == str((project_root / "data" / "models" / "yolov8s.pt").resolve())
    assert settings["validation"]["save_dir"] == str((project_root / "result" / "gui_val").resolve())
    assert settings["validation"]["source_path"] == str((project_root / "images" / "demo.jpg").resolve())


def test_settings_service_preserves_model_bare_name_for_portable_download_target(tmp_path):
    from scr.services.settings_service import SettingsService

    project_root = tmp_path / "project-model-name"
    service = SettingsService(project_root=project_root)
    settings = service.load()
    settings["training"]["pretrained"] = "custom.pt"
    settings["training"]["base_model"] = "custom.pt"

    service.save(settings)
    persisted = json.loads(service.settings_path.read_text(encoding="utf-8"))
    reloaded = service.load()

    assert persisted["training"]["pretrained"] == "custom.pt"
    assert reloaded["training"]["pretrained"] == "custom.pt"
