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
    assert saved["validation"]["save_dir"] == str(Path("result") / "gui_predict")


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
                    "save_dir": "result/gui_predict",
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
    assert settings["validation"]["save_dir"] == str((project_root / "result" / "gui_predict").resolve())
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


def test_conversion_config_rejects_invalid_ratios(tmp_path):
    from scr.services.conversion_service import ConversionConfig

    config = ConversionConfig(
        task_mode="obb",
        images_dir=tmp_path,
        annotations_dir=tmp_path,
        output_dir=tmp_path / "data",
        labels_dir=tmp_path / "labels",
        class_names=["weld"],
        train_ratio=0.8,
        val_ratio=0.2,
        test_ratio=0.2,
    )

    with pytest.raises(ValueError, match="比例"):
        config.validate()


def test_run_conversion_writes_obb_and_detect_formats(tmp_path):
    from scr.services.conversion_service import ConversionConfig, run_conversion

    images = tmp_path / "images"
    images.mkdir()
    make_image(images / "obb.jpg")
    (images / "obb.json").write_text(
        json.dumps(
            {
                "imageWidth": 100,
                "imageHeight": 100,
                "shapes": [
                    {
                        "label": "weld",
                        "shape_type": "oriented_rectangle",
                        "points": [[10, 20], [80, 20], [80, 30], [10, 30]],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    run_conversion(
        ConversionConfig(
            task_mode="obb",
            images_dir=images,
            annotations_dir=images,
            output_dir=tmp_path / "data_obb",
            labels_dir=tmp_path / "labels_obb",
            class_names=["weld"],
            train_ratio=1.0,
            val_ratio=0.0,
            test_ratio=0.0,
        )
    )
    assert (tmp_path / "data_obb" / "train" / "labels" / "obb.txt").read_text(encoding="utf-8").strip() == (
        "0 0.100000 0.200000 0.800000 0.200000 0.800000 0.300000 0.100000 0.300000"
    )

    make_image(images / "box.jpg")
    (images / "box.json").write_text(
        json.dumps(
            {
                "imageWidth": 100,
                "imageHeight": 100,
                "shapes": [{"label": "weld", "shape_type": "rectangle", "points": [[10, 20], [30, 60]]}],
            }
        ),
        encoding="utf-8",
    )
    run_conversion(
        ConversionConfig(
            task_mode="detect",
            images_dir=images,
            annotations_dir=images,
            output_dir=tmp_path / "data_detect",
            labels_dir=tmp_path / "labels_detect",
            class_names=["weld"],
            train_ratio=1.0,
            val_ratio=0.0,
            test_ratio=0.0,
        )
    )
    assert "0 0.200000 0.400000 0.200000 0.400000" in (
        tmp_path / "data_detect" / "train" / "labels" / "box.txt"
    ).read_text(encoding="utf-8")


def test_line_conversion_expands_to_obb(tmp_path):
    from scr.services.conversion_service import ConversionConfig, run_conversion

    images = tmp_path / "images"
    images.mkdir()
    make_image(images / "line.jpg")
    (images / "line.json").write_text(
        json.dumps(
            {
                "imageWidth": 100,
                "imageHeight": 100,
                "shapes": [{"label": "weld", "shape_type": "line", "points": [[10, 50], [90, 50]]}],
            }
        ),
        encoding="utf-8",
    )

    run_conversion(
        ConversionConfig(
            task_mode="obb",
            images_dir=images,
            annotations_dir=images,
            output_dir=tmp_path / "data",
            labels_dir=tmp_path / "labels",
            class_names=["weld"],
            train_ratio=1.0,
            val_ratio=0.0,
            test_ratio=0.0,
            line_half_width=10,
        )
    )

    assert (tmp_path / "data" / "train" / "labels" / "line.txt").read_text(encoding="utf-8").strip() == (
        "0 0.100000 0.600000 0.900000 0.600000 0.900000 0.400000 0.100000 0.400000"
    )


def test_conversion_can_split_existing_yolo_labels_without_labelme(tmp_path):
    from scr.services.conversion_service import ConversionConfig, run_conversion

    images = tmp_path / "images"
    labels = tmp_path / "yolo_labels"
    images.mkdir()
    labels.mkdir()
    for name in ("1", "2", "3"):
        make_image(images / f"{name}.jpg")
        (labels / f"{name}.txt").write_text("0 0.5 0.5 0.2 0.2\n", encoding="utf-8")

    result = run_conversion(
        ConversionConfig(
            task_mode="detect",
            source_format="yolo",
            images_dir=images,
            annotations_dir=labels,
            output_dir=tmp_path / "data",
            labels_dir=tmp_path / "labels",
            class_names=["weld"],
            train_ratio=1.0,
            val_ratio=0.0,
            test_ratio=0.0,
        )
    )

    assert result.labeled_train_count == 3
    assert result.total_boxes == 3
    assert (tmp_path / "data" / "train" / "labels" / "1.txt").read_text(encoding="utf-8") == "0 0.5 0.5 0.2 0.2\n"
    assert (tmp_path / "labels" / "2.txt").exists()


def test_conversion_tracks_multi_class_stats_and_formats_result(tmp_path):
    from scr.services.conversion_service import ConversionConfig, format_conversion_result, run_conversion

    images = tmp_path / "images"
    images.mkdir()
    make_image(images / "multi.jpg")
    (images / "multi.json").write_text(
        json.dumps(
            {
                "imageWidth": 100,
                "imageHeight": 100,
                "shapes": [
                    {"label": "weld", "shape_type": "rectangle", "points": [[10, 10], [30, 30]]},
                    {"label": "scratch", "shape_type": "rectangle", "points": [[40, 40], [50, 60]]},
                    {"label": "unknown", "shape_type": "rectangle", "points": [[70, 70], [80, 90]]},
                ],
            }
        ),
        encoding="utf-8",
    )
    config = ConversionConfig(
        task_mode="detect",
        source_format="labelme",
        images_dir=images,
        annotations_dir=images,
        output_dir=tmp_path / "data",
        labels_dir=tmp_path / "labels",
        class_names=["weld", "scratch"],
        train_ratio=1.0,
        val_ratio=0.0,
        test_ratio=0.0,
    )

    result = run_conversion(config)
    report = format_conversion_result(result, config)

    assert result.stats["train"] == {"weld": 1, "scratch": 1}
    assert "转换完成" in report
    assert "训练集（train）: 1 张图片, 2 个标注" in report
    assert "weld: train=1, val=0, test=0, total=1" in report
    assert "scratch: train=1, val=0, test=0, total=1" in report
    assert "标签 'unknown'" in report
    assert str(result.yaml_path) in report


def test_preview_conversion_reports_real_box_counts(tmp_path):
    from scr.services.conversion_service import ConversionConfig, preview_conversion

    images = tmp_path / "images"
    images.mkdir()
    make_image(images / "multi.jpg")
    (images / "multi.json").write_text(
        json.dumps(
            {
                "imageWidth": 100,
                "imageHeight": 100,
                "shapes": [
                    {"label": "weld", "shape_type": "rectangle", "points": [[10, 10], [30, 30]]},
                    {"label": "scratch", "shape_type": "rectangle", "points": [[40, 40], [60, 60]]},
                ],
            }
        ),
        encoding="utf-8",
    )

    result = preview_conversion(
        ConversionConfig(
            task_mode="detect",
            source_format="labelme",
            images_dir=images,
            annotations_dir=images,
            output_dir=tmp_path / "data",
            labels_dir=tmp_path / "labels",
            class_names=[],
            train_ratio=1.0,
            val_ratio=0.0,
            test_ratio=0.0,
        )
    )

    assert result.labeled_train_count == 1
    assert result.total_boxes == 2
    assert result.stats["train"] == {"weld": 1, "scratch": 1}


def test_conversion_auto_detects_labelme_classes(tmp_path):
    from scr.services.conversion_service import ConversionConfig, run_conversion

    images = tmp_path / "images"
    images.mkdir()
    make_image(images / "multi.jpg")
    (images / "multi.json").write_text(
        json.dumps(
            {
                "imageWidth": 100,
                "imageHeight": 100,
                "shapes": [
                    {"label": "scratch", "shape_type": "rectangle", "points": [[40, 40], [50, 60]]},
                    {"label": "weld", "shape_type": "rectangle", "points": [[10, 10], [30, 30]]},
                ],
            }
        ),
        encoding="utf-8",
    )

    result = run_conversion(
        ConversionConfig(
            task_mode="detect",
            source_format="labelme",
            images_dir=images,
            annotations_dir=images,
            output_dir=tmp_path / "data",
            labels_dir=tmp_path / "labels",
            class_names=[],
            train_ratio=1.0,
            val_ratio=0.0,
            test_ratio=0.0,
        )
    )

    assert result.class_names == ["scratch", "weld"]
    assert result.stats["train"] == {"scratch": 1, "weld": 1}
    assert "names: ['scratch', 'weld']" in (tmp_path / "data" / "data.yaml").read_text(encoding="utf-8")


def test_conversion_auto_names_existing_yolo_classes(tmp_path):
    from scr.services.conversion_service import ConversionConfig, run_conversion

    images = tmp_path / "images"
    labels = tmp_path / "labels_in"
    images.mkdir()
    labels.mkdir()
    make_image(images / "one.jpg")
    (labels / "one.txt").write_text("2 0.5 0.5 0.2 0.2\n0 0.4 0.4 0.1 0.1\n", encoding="utf-8")

    result = run_conversion(
        ConversionConfig(
            task_mode="detect",
            source_format="yolo",
            images_dir=images,
            annotations_dir=labels,
            output_dir=tmp_path / "data",
            labels_dir=tmp_path / "labels_out",
            class_names=[],
            train_ratio=1.0,
            val_ratio=0.0,
            test_ratio=0.0,
        )
    )

    assert result.class_names == ["class_0", "class_1", "class_2"]
    assert result.stats["train"] == {"class_2": 1, "class_0": 1}


def test_annotation_preview_services(tmp_path):
    from scr.services.annotation_service import Annotation, load_yolo_annotations, render_annotation_preview

    image_path = tmp_path / "a.jpg"
    make_image(image_path)
    label = tmp_path / "a.txt"
    label.write_text("0 0.5 0.5 0.2 0.4\n", encoding="utf-8")

    annotations = load_yolo_annotations((100, 100), label, "detect", ["weld"])
    preview = render_annotation_preview(image_path, [Annotation(0, "weld", annotations[0].points)])

    assert annotations[0].points == [(40.0, 30.0), (60.0, 30.0), (60.0, 70.0), (40.0, 70.0)]
    assert preview.size == (100, 100)


def test_annotation_preview_auto_detects_obb_labels(tmp_path):
    from scr.services.annotation_service import load_yolo_annotations, render_annotation_preview

    image_path = tmp_path / "obb.jpg"
    make_image(image_path, size=(100, 100), color="white")
    label = tmp_path / "obb.txt"
    label.write_text(
        "0 0.1 0.2 0.8 0.2 0.8 0.3 0.1 0.3\n",
        encoding="utf-8",
    )

    annotations = load_yolo_annotations((100, 100), label, "detect", ["weld"])
    preview = render_annotation_preview(image_path, annotations)

    assert annotations[0].points == [(10.0, 20.0), (80.0, 20.0), (80.0, 30.0), (10.0, 30.0)]
    assert preview.size == (100, 100)


def test_rename_preview_execute_and_conflict(tmp_path):
    from scr.services.rename_service import execute_rename, preview_rename

    (tmp_path / "a.jpg").write_bytes(b"a")
    plan = preview_rename(tmp_path, "W", 1, 2)
    result = execute_rename(plan)
    assert result.renamed_count == 1
    assert (tmp_path / "W01.jpg").exists()

    (tmp_path / "b.jpg").write_bytes(b"b")
    conflict_plan = preview_rename(tmp_path, "W", 1, 2)
    assert conflict_plan[0].conflict is True


def test_rename_preview_uses_natural_numeric_sort(tmp_path):
    from scr.services.rename_service import preview_rename

    for name in ["1.jpg", "10.jpg", "100.jpg", "2.jpg", "3.jpg"]:
        (tmp_path / name).write_bytes(b"image")

    plan = preview_rename(tmp_path, "", 1, 1)

    assert [item.old_name for item in plan] == ["1.jpg", "2.jpg", "3.jpg", "10.jpg", "100.jpg"]
    assert [item.new_name for item in plan] == ["1.jpg", "2.jpg", "3.jpg", "4.jpg", "5.jpg"]


def test_resize_preview_and_run(tmp_path):
    from scr.services.resize_service import ResizeConfig, preview_resize, run_resize

    source = tmp_path / "images"
    source.mkdir()
    make_image(source / "a.jpg", size=(1920, 1080), color="red")
    config = ResizeConfig(
        source,
        tmp_path / "out",
        tmp_path / "backup",
        960,
        960,
        "white",
        True,
    )

    preview = preview_resize(config)
    result = run_resize(config)

    from PIL import Image

    assert preview.items[0].scale == 0.5
    assert preview.items[0].resized_size == (960, 540)
    assert Image.open(tmp_path / "out" / "a.jpg").size == (960, 960)
    assert (tmp_path / "backup" / "a.jpg").exists()
    assert result.processed_count == 1


def test_resize_can_skip_backup_by_default(tmp_path):
    from scr.services.resize_service import ResizeConfig, run_resize

    source = tmp_path / "images"
    source.mkdir()
    make_image(source / "a.jpg", size=(640, 480), color="blue")

    result = run_resize(
        ResizeConfig(
            source_dir=source,
            output_dir=tmp_path / "out",
            backup_dir=tmp_path / "backup",
            long_edge=320,
            canvas_size=320,
            background="white",
            backup_enabled=False,
        )
    )

    assert result.processed_count == 1
    assert (tmp_path / "out" / "a.jpg").exists()
    assert not (tmp_path / "backup").exists()


def test_resize_recursively_scans_and_preserves_relative_structure(tmp_path):
    from scr.services.resize_service import ResizeConfig, preview_resize, run_resize

    source = tmp_path / "images"
    nested = source / "10" / "2"
    nested.mkdir(parents=True)
    make_image(source / "1.jpg", size=(1000, 500), color="red")
    make_image(source / "10.jpg", size=(500, 1000), color="green")
    make_image(nested / "3.jpg", size=(1200, 600), color="blue")

    config = ResizeConfig(
        source_dir=source,
        output_dir=tmp_path / "out",
        backup_dir=tmp_path / "backup",
        canvas_size=800,
        background="white",
        backup_enabled=True,
    )

    preview = preview_resize(config)
    result = run_resize(config)

    assert [str(item.source.relative_to(source)) for item in preview.items] == [
        "1.jpg",
        str(Path("10") / "2" / "3.jpg"),
        "10.jpg",
    ]
    assert [item.output.relative_to(tmp_path / "out") for item in preview.items] == [
        Path("1.jpg"),
        Path("10") / "2" / "3.jpg",
        Path("10.jpg"),
    ]
    assert (tmp_path / "out" / "10" / "2" / "3.jpg").exists()
    assert (tmp_path / "backup" / "10" / "2" / "3.jpg").exists()
    assert result.processed_count == 3


def test_conversion_supports_class_mapping_and_backup_folder(tmp_path):
    from scr.services.conversion_service import ConversionConfig, run_conversion

    images = tmp_path / "images"
    images.mkdir()
    make_image(images / "multi.jpg")
    (images / "multi.json").write_text(
        json.dumps(
            {
                "imageWidth": 100,
                "imageHeight": 100,
                "shapes": [
                    {"label": "a", "shape_type": "rectangle", "points": [[10, 10], [30, 30]]},
                    {"label": "b", "shape_type": "rectangle", "points": [[40, 40], [60, 60]]},
                    {"label": "c", "shape_type": "rectangle", "points": [[65, 65], [80, 80]]},
                ],
            }
        ),
        encoding="utf-8",
    )

    result = run_conversion(
        ConversionConfig(
            task_mode="detect",
            source_format="labelme",
            images_dir=images,
            annotations_dir=images,
            output_dir=tmp_path / "data",
            labels_dir=tmp_path / "labels",
            train_ratio=1.0,
            val_ratio=0.0,
            test_ratio=0.0,
            backup_yolo_files=True,
            class_name_mapping={"a": "merged", "b": "merged", "c": "solo"},
        )
    )

    label_text = (tmp_path / "data" / "train" / "labels" / "multi.txt").read_text(
        encoding="utf-8"
    )

    assert result.class_names == ["merged", "solo"]
    assert "0 " in label_text
    assert "1 " in label_text
    assert result.backup_dir is not None
    assert (result.backup_dir / "data.yaml").exists()
    assert (result.backup_dir / "labels" / "multi.txt").exists()


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
    from scr.ui import helpers

    project_root = tmp_path / "project"
    app_root = tmp_path / "app"
    (project_root / "data" / "models").mkdir(parents=True)
    (app_root / "data" / "models").mkdir(parents=True)
    (project_root / "data" / "models" / "shared.pt").write_text("project", encoding="utf-8")
    (project_root / "data" / "models" / "project-only.pt").write_text("project", encoding="utf-8")
    (app_root / "data" / "models" / "shared.pt").write_text("app", encoding="utf-8")
    (app_root / "data" / "models" / "app-only.pt").write_text("app", encoding="utf-8")

    monkeypatch.setattr(helpers, "ROOT", app_root)

    names = helpers.find_training_model_names(project_root)
    shared_resolved = helpers.resolve_training_model_reference("shared.pt", project_root)
    app_only_resolved = helpers.resolve_training_model_reference("app-only.pt", project_root)
    missing_resolved = helpers.resolve_training_model_reference("missing.pt", project_root)

    assert names == ["project-only.pt", "shared.pt", "app-only.pt"]
    assert shared_resolved == str((project_root / "data" / "models" / "shared.pt").resolve())
    assert app_only_resolved == str((app_root / "data" / "models" / "app-only.pt").resolve())
    assert missing_resolved == str((project_root / "data" / "models" / "missing.pt").resolve())


def test_validation_model_choices_include_result_best_and_optional_last(tmp_path):
    from scr.ui.helpers import find_models_full_paths

    run_dir = tmp_path / "result" / "train-2" / "weights"
    run_dir.mkdir(parents=True)
    (run_dir / "best.pt").write_text("best", encoding="utf-8")
    (run_dir / "last.pt").write_text("last", encoding="utf-8")

    with_last = find_models_full_paths(tmp_path / "result", show_last_training_models=True)
    without_last = find_models_full_paths(
        tmp_path / "result", show_last_training_models=False
    )

    assert [path.name for path in with_last] == ["best.pt", "last.pt"]
    assert [path.name for path in without_last] == ["best.pt"]


def test_training_model_helpers_avoid_duplicate_scan_when_project_is_app_root(tmp_path):
    from scr.ui.helpers import find_training_model_names

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


def test_detection_source_collection_supports_folder_and_single_file(tmp_path):
    from scr.services.detection_service import collect_prediction_sources

    folder = tmp_path / "inputs"
    folder.mkdir()
    image = folder / "a.jpg"
    video = folder / "b.mp4"
    ignored = folder / "c.txt"
    image.write_bytes(b"image")
    video.write_bytes(b"video")
    ignored.write_text("skip", encoding="utf-8")

    assert collect_prediction_sources("图片/视频文件夹", folder) == [image, video]
    assert collect_prediction_sources("图片/视频", image) == [image]
    assert collect_prediction_sources("图片/视频", video) == [video]
    assert collect_prediction_sources("摄像头", folder) == []


def test_detection_source_collection_uses_natural_numeric_sort(tmp_path):
    from scr.services.detection_service import collect_prediction_sources

    folder = tmp_path / "inputs"
    folder.mkdir()
    for name in ["1.jpg", "10.jpg", "100.jpg", "2.jpg", "3.jpg"]:
        (folder / name).write_bytes(b"image")

    assert [path.name for path in collect_prediction_sources("图片/视频文件夹", folder)] == [
        "1.jpg",
        "2.jpg",
        "3.jpg",
        "10.jpg",
        "100.jpg",
    ]


def test_stream_result_rendering_uses_current_frame_as_plot_background():
    import numpy as np
    from scr.services.detection_service import render_result_image_from_frame

    class FakeResult:
        def __init__(self):
            self.received = None

        def plot(self, img=None):
            self.received = img.copy() if img is not None else None
            return img

    frame = np.full((4, 5, 3), 127, dtype=np.uint8)
    result = FakeResult()

    rendered = render_result_image_from_frame(result, frame)

    assert result.received is not None
    assert np.array_equal(result.received, frame)
    assert rendered.size == (5, 4)


def test_ultralytics_compat_patches_missing_cv2_highgui_symbols(monkeypatch):
    from scr.services.ultralytics_compat import ensure_cv2_highgui_compat

    fake_cv2 = SimpleNamespace()
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)

    ensure_cv2_highgui_compat()

    assert callable(fake_cv2.imshow)
    assert callable(fake_cv2.namedWindow)
    assert callable(fake_cv2.destroyAllWindows)
    assert fake_cv2.waitKey() == -1


def test_cached_call_reuses_value_until_ttl_expires(monkeypatch):
    from scr.services.environment_service import cached_call

    now = {"value": 10.0}
    calls = {"count": 0}

    def clock():
        return now["value"]

    def expensive():
        calls["count"] += 1
        return {"count": calls["count"]}

    first = cached_call("unit-test-cache", 5.0, expensive, clock=clock)
    second = cached_call("unit-test-cache", 5.0, expensive, clock=clock)
    now["value"] = 16.0
    third = cached_call("unit-test-cache", 5.0, expensive, clock=clock)

    assert first == {"count": 1}
    assert second == {"count": 1}
    assert third == {"count": 2}


def test_system_status_uses_short_cache_and_nonzero_sampling(monkeypatch):
    from scr.services import environment_service

    calls = {}

    class Mem:
        used = 12 * 1024**3
        total = 32 * 1024**3

    class Disk:
        used = 100 * 1024**3
        total = 200 * 1024**3

    monkeypatch.setattr(environment_service, "cached_call", lambda key, ttl_seconds, loader, clock=None: (calls.setdefault("ttl", ttl_seconds), loader())[1])

    class PsutilStub:
        @staticmethod
        def virtual_memory():
            return Mem()

        @staticmethod
        def disk_usage(_path):
            return Disk()

        @staticmethod
        def cpu_percent(interval=0.0):
            calls["interval"] = interval
            return 7.5

        @staticmethod
        def cpu_count():
            return 32

    monkeypatch.setitem(environment_service._load_system_status.__globals__, "psutil", PsutilStub)
    import builtins
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "psutil":
            return PsutilStub
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    def fake_run(*args, **kwargs):
        calls["creationflags"] = kwargs.get("creationflags")
        return type("R", (), {"returncode": 1, "stdout": ""})()

    monkeypatch.setattr(environment_service.subprocess, "run", fake_run)

    status = environment_service.system_status()

    assert calls["ttl"] == 0.5
    assert calls["interval"] == 0.1
    assert calls["creationflags"] == getattr(environment_service.subprocess, "CREATE_NO_WINDOW", 0)
    assert status["cpu"] == "7.5% / 32核"


def test_logged_process_uses_hidden_windows_subprocess(monkeypatch):
    from queue import Queue

    from scr.services import runtime_service

    calls = {}

    class FakeStdout:
        def __iter__(self):
            return iter(())

    class FakeProcess:
        stdout = FakeStdout()

        def wait(self):
            return 0

    def fake_popen(command, **kwargs):
        calls["command"] = command
        calls["creationflags"] = kwargs.get("creationflags")
        return FakeProcess()

    monkeypatch.setattr(runtime_service.subprocess, "Popen", fake_popen)

    handle = runtime_service.spawn_logged_process(["demo"], str(Path.cwd()), Queue())
    handle.thread.join(timeout=1)

    assert calls["command"] == ["demo"]
    assert calls["creationflags"] == getattr(runtime_service.subprocess, "CREATE_NO_WINDOW", 0)


def test_sanitize_terminal_line_removes_ansi_sequences():
    from scr.services.runtime_service import sanitize_terminal_line

    raw = "\x1b[K\x1b[34m\x1b[1mtrain: \x1b[0mScanning labels.cache... 91/91 0.0s\r\n"

    assert sanitize_terminal_line(raw) == "train: Scanning labels.cache... 91/91 0.0s"


def test_logged_process_cleans_terminal_escape_sequences(monkeypatch):
    from queue import Queue

    from scr.services import runtime_service

    class FakeStdout:
        def __iter__(self):
            return iter(
                (
                    "\x1b[K1/500 640: 5% 1/20 1.1it/s\r\n",
                    "\x1b[34moptimizer:\x1b[0m AdamW(lr=0.002)\n",
                    "\x1b[K\r\n",
                )
            )

    class FakeProcess:
        stdout = FakeStdout()

        def wait(self):
            return 0

    monkeypatch.setattr(runtime_service.subprocess, "Popen", lambda *_args, **_kwargs: FakeProcess())

    queue = Queue()
    handle = runtime_service.spawn_logged_process(["demo"], str(Path.cwd()), queue)
    handle.thread.join(timeout=1)

    assert queue.get(timeout=1) == ("log", "1/500 640: 5% 1/20 1.1it/s")
    assert queue.get(timeout=1) == ("log", "optimizer: AdamW(lr=0.002)")
    assert queue.get(timeout=1) == ("exit", 0)


def test_rename_can_include_matching_labels_and_blocks_label_conflicts(tmp_path):
    from scr.services.rename_service import execute_rename, preview_rename

    images = tmp_path / "images"
    labels = tmp_path / "labels"
    images.mkdir()
    labels.mkdir()
    (images / "2.jpg").write_bytes(b"image")
    (labels / "1.txt").write_text("old", encoding="utf-8")
    (labels / "2.txt").write_text("match", encoding="utf-8")

    blocked = preview_rename(images, "", 1, 1, labels_dir=labels, include_labels=True)
    assert blocked[0].label_conflict is True
    assert execute_rename(blocked).renamed_count == 0
    assert (images / "2.jpg").exists()
    assert (labels / "2.txt").exists()

    (labels / "1.txt").unlink()
    plan = preview_rename(images, "A", 1, 1, labels_dir=labels, include_labels=True)
    assert plan[0].conflict is False
    assert plan[0].label_target == labels / "A1.txt"
    result = execute_rename(plan)
    assert result.renamed_count == 1
    assert result.label_renamed_count == 1
    assert (images / "A1.jpg").exists()
    assert (labels / "A1.txt").read_text(encoding="utf-8") == "match"


def test_rename_can_include_labelme_and_yolo_labels_separately(tmp_path):
    from scr.services.rename_service import execute_rename, preview_rename

    images = tmp_path / "images"
    labelme = tmp_path / "labelme"
    yolo = tmp_path / "yolo"
    images.mkdir()
    labelme.mkdir()
    yolo.mkdir()
    (images / "2.jpg").write_bytes(b"image")
    (labelme / "2.json").write_text("labelme", encoding="utf-8")
    (yolo / "2.txt").write_text("yolo", encoding="utf-8")

    plan = preview_rename(
        images,
        "A",
        1,
        1,
        labelme_dir=labelme,
        include_labelme=True,
        labels_dir=yolo,
        include_labels=True,
    )

    assert plan[0].labelme_source == labelme / "2.json"
    assert plan[0].labelme_target == labelme / "A1.json"
    assert plan[0].label_source == yolo / "2.txt"
    assert plan[0].label_target == yolo / "A1.txt"
    result = execute_rename(plan)
    assert result.renamed_count == 1
    assert result.labelme_renamed_count == 1
    assert result.label_renamed_count == 1
    assert (images / "A1.jpg").exists()
    assert (labelme / "A1.json").read_text(encoding="utf-8") == "labelme"
    assert (yolo / "A1.txt").read_text(encoding="utf-8") == "yolo"

