import json
import os
from pathlib import Path

import pytest


def make_image(path: Path, size=(100, 100), color="white"):
    from PIL import Image

    Image.new("RGB", size, color).save(path)


def test_settings_service_loads_and_merges_defaults(tmp_path):
    from scr.yolo_workbench.services.settings_service import SettingsService

    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps({"training": {"epochs": 12}}, ensure_ascii=False), encoding="utf-8")

    settings = SettingsService(settings_path=settings_path, project_root=tmp_path).load()

    assert settings["project"]["root"] == str(tmp_path)
    assert settings["training"]["epochs"] == 12
    assert settings["training"]["batch"] == 16
    assert settings["image_resize"]["canvas_size"] == 960


def test_conversion_config_rejects_invalid_ratios(tmp_path):
    from scr.yolo_workbench.services.conversion_service import ConversionConfig

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
    from scr.yolo_workbench.services.conversion_service import ConversionConfig, run_conversion

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
    from scr.yolo_workbench.services.conversion_service import ConversionConfig, run_conversion

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


def test_annotation_preview_services(tmp_path):
    from scr.yolo_workbench.services.annotation_service import Annotation, load_yolo_annotations, render_annotation_preview

    image_path = tmp_path / "a.jpg"
    make_image(image_path)
    label = tmp_path / "a.txt"
    label.write_text("0 0.5 0.5 0.2 0.4\n", encoding="utf-8")

    annotations = load_yolo_annotations((100, 100), label, "detect", ["weld"])
    preview = render_annotation_preview(image_path, [Annotation(0, "weld", annotations[0].points)])

    assert annotations[0].points == [(40.0, 30.0), (60.0, 30.0), (60.0, 70.0), (40.0, 70.0)]
    assert preview.size == (100, 100)


def test_rename_preview_execute_and_conflict(tmp_path):
    from scr.yolo_workbench.services.rename_service import execute_rename, preview_rename

    (tmp_path / "a.jpg").write_bytes(b"a")
    plan = preview_rename(tmp_path, "W", 1, 2)
    result = execute_rename(plan)
    assert result.renamed_count == 1
    assert (tmp_path / "W01.jpg").exists()

    (tmp_path / "b.jpg").write_bytes(b"b")
    conflict_plan = preview_rename(tmp_path, "W", 1, 2)
    assert conflict_plan[0].conflict is True


def test_resize_preview_and_run(tmp_path):
    from scr.yolo_workbench.services.resize_service import ResizeConfig, preview_resize, run_resize

    source = tmp_path / "images"
    source.mkdir()
    make_image(source / "a.jpg", size=(1920, 1080), color="red")
    config = ResizeConfig(source, tmp_path / "out", tmp_path / "backup", 960, 960, "white")

    preview = preview_resize(config)
    result = run_resize(config)

    from PIL import Image

    assert preview.items[0].scale == 0.5
    assert preview.items[0].resized_size == (960, 540)
    assert Image.open(tmp_path / "out" / "a.jpg").size == (960, 960)
    assert (tmp_path / "backup" / "a.jpg").exists()
    assert result.processed_count == 1


def test_training_command_and_detection_helpers(tmp_path):
    from scr.yolo_workbench.services.detection_service import normalize_detection_item, scan_candidate_models
    from scr.yolo_workbench.services.training_service import build_train_command, infer_task_mode_from_model

    command = build_train_command(
        {"model_yaml": "data/yolov8m-obb.yaml", "data": "data.yaml", "epochs": 800, "lr": 0.001}
    )
    assert command[:5] == ["pixi", "run", "yolo", "obb", "train"]
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


def test_training_command_includes_all_hsv_params_when_configured():
    from scr.yolo_workbench.services.training_service import build_train_command

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


def test_detection_source_collection_supports_folder_and_single_file(tmp_path):
    from scr.yolo_workbench.services.detection_service import collect_prediction_sources

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
    from scr.yolo_workbench.services.detection_service import collect_prediction_sources

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


def test_cached_call_reuses_value_until_ttl_expires(monkeypatch):
    from scr.yolo_workbench.services.environment_service import cached_call

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
    from scr.yolo_workbench.services import environment_service

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
    monkeypatch.setattr(environment_service.subprocess, "run", lambda *args, **kwargs: type("R", (), {"returncode": 1, "stdout": ""})())

    status = environment_service.system_status()

    assert calls["ttl"] == 0.5
    assert calls["interval"] == 0.1
    assert status["cpu"] == "7.5% / 32核"


def test_rename_can_include_matching_labels_and_blocks_label_conflicts(tmp_path):
    from scr.yolo_workbench.services.rename_service import execute_rename, preview_rename

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
