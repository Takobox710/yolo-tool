import json

import os

import sys

from pathlib import Path

from types import SimpleNamespace

import pytest

def make_image(path: Path, size=(100, 100), color="white"):
    from PIL import Image

    Image.new("RGB", size, color).save(path)


def test_conversion_config_rejects_invalid_ratios(tmp_path):
    from src.services.conversion import ConversionConfig

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
    from src.services.conversion import ConversionConfig, run_conversion

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
    from src.services.conversion import ConversionConfig, run_conversion

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
    from src.services.conversion import ConversionConfig, run_conversion

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
    assert not (tmp_path / "data" / "old").exists()
    assert not (tmp_path / "data" / "val").exists()
    assert not (tmp_path / "data" / "test").exists()

    yaml_text = (tmp_path / "data" / "data.yaml").read_text(encoding="utf-8")
    assert "train: data/train/images" in yaml_text
    assert "val:" not in yaml_text
    assert "test:" not in yaml_text


def test_conversion_auto_detects_labelme_classes(tmp_path):
    from src.services.conversion import ConversionConfig, run_conversion

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


def test_conversion_supports_class_mapping_and_backup_folder(tmp_path):
    from src.services.conversion import ConversionConfig, run_conversion

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


def test_conversion_skips_empty_split_directories_even_when_ratio_is_nonzero(tmp_path):
    from src.services.conversion import ConversionConfig, run_conversion

    images = tmp_path / "images"
    images.mkdir()
    make_image(images / "one.jpg")
    (images / "one.json").write_text(
        json.dumps(
            {
                "imageWidth": 100,
                "imageHeight": 100,
                "shapes": [
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
            class_names=["weld"],
            train_ratio=0.0,
            val_ratio=1.0,
            test_ratio=0.0,
        )
    )

    assert result.labeled_train_count == 0
    assert result.labeled_val_count == 1
    assert result.labeled_test_count == 0
    assert not (tmp_path / "data" / "train").exists()
    assert (tmp_path / "data" / "val" / "labels" / "one.txt").exists()
    assert not (tmp_path / "data" / "test").exists()

    yaml_text = (tmp_path / "data" / "data.yaml").read_text(encoding="utf-8")
    assert "train:" not in yaml_text
    assert "val: data/val/images" in yaml_text
    assert "test:" not in yaml_text
