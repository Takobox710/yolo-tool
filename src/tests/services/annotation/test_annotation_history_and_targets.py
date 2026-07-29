import json

import os

import sys

from pathlib import Path

from types import SimpleNamespace

import pytest

def make_image(path: Path, size=(100, 100), color="white"):
    from PIL import Image

    Image.new("RGB", size, color).save(path)


def test_annotation_history_keeps_immutable_values_and_only_five_undo_steps():
    from src.services.annotation import EditableAnnotation
    from src.services.annotation.history import AnnotationHistory

    history = AnnotationHistory(limit=5)
    image_path = Path("image.jpg")
    for index in range(6):
        before = []
        after = [
            EditableAnnotation(
                0,
                "rect",
                [(index, 0), (index + 10, 0), (index + 10, 10), (index, 10)],
            )
        ]
        history.record(image_path, before, after, 0)
        after[0].points[0] = (999, 999)

    entries = [history.pop_undo() for _ in range(5)]

    assert all(entry is not None for entry in entries)
    assert entries[0].after[0].points[0] == (5.0, 0.0)
    assert entries[-1].after[0].points[0] == (1.0, 0.0)
    assert history.pop_undo() is None



def test_annotation_history_ignores_equal_snapshots_and_clears_redo_on_new_edit():
    from src.services.annotation import EditableAnnotation
    from src.services.annotation.history import AnnotationHistory

    history = AnnotationHistory()
    annotation = EditableAnnotation(
        0, "rect", [(0, 0), (10, 0), (10, 10), (0, 10)]
    )

    assert history.record(Path("image.jpg"), [], [], None) is False
    assert history.record(Path("image.jpg"), [], [annotation], 0) is True
    history.pop_undo()
    assert history.can_redo is True
    assert history.record(Path("image.jpg"), [], [annotation], 0) is True
    assert history.can_redo is False



def test_collect_ai_target_images_supports_following_and_custom_ranges(tmp_path):
    from src.services.annotation import collect_ai_target_images

    images = [tmp_path / f"{index}.jpg" for index in range(1, 5)]
    annotations_dir = tmp_path / "annotations"
    labels_dir = tmp_path / "labels"
    annotations_dir.mkdir()
    labels_dir.mkdir()

    following = collect_ai_target_images(
        images,
        images[1],
        annotations_dir,
        labels_dir,
        "当前及以后图片",
        current_index=1,
    )
    custom = collect_ai_target_images(
        images,
        images[0],
        annotations_dir,
        labels_dir,
        "自定义图片",
        selected_images=[images[0], images[2], tmp_path / "other.jpg"],
    )

    assert following == images[1:]
    assert custom == [images[0], images[2]]



def test_annotation_file_index_scans_images_and_detects_existing_annotations(tmp_path):
    from src.services.annotation import collect_annotation_presence, scan_annotation_image_items

    images_dir = tmp_path / "images"
    annotations_dir = tmp_path / "annotations"
    labels_dir = tmp_path / "labels"
    images_dir.mkdir()
    annotations_dir.mkdir()
    labels_dir.mkdir()

    make_image(images_dir / "2.jpg")
    make_image(images_dir / "10.png")
    make_image(images_dir / "1.bmp")
    (annotations_dir / "2.json").write_text(
        json.dumps({"shapes": [{"label": "weld"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (labels_dir / "10.txt").write_text("0 0.5 0.5 0.2 0.2\n", encoding="utf-8")
    (labels_dir / "1.txt").write_text("\n", encoding="utf-8")

    image_items = scan_annotation_image_items(images_dir)
    statuses = collect_annotation_presence(image_items, annotations_dir, labels_dir)

    assert [path.name for path in image_items] == ["1.bmp", "2.jpg", "10.png"]
    assert statuses[str((images_dir / "1.bmp").resolve())] is False
    assert statuses[str((images_dir / "2.jpg").resolve())] is True
    assert statuses[str((images_dir / "10.png").resolve())] is True



def test_detect_yolo_mode_uses_sorted_first_valid_files_and_handles_empty_files(tmp_path):
    from src.services.annotation import detect_yolo_mode

    labels = tmp_path / "labels"
    labels.mkdir()
    (labels / "0-empty.txt").write_text("\n", encoding="utf-8")
    (labels / "2-detect.txt").write_text("0 0.5 0.5 0.2 0.2\n", encoding="utf-8")
    (labels / "1-invalid.txt").write_text("bad data\n", encoding="utf-8")

    assert detect_yolo_mode(labels) == "detect"



def test_detect_yolo_mode_applies_obb_seg_ambiguity_rule(tmp_path):
    from src.services.annotation import detect_yolo_mode

    labels = tmp_path / "labels"
    labels.mkdir()
    (labels / "1.txt").write_text("0 0 0 1 0 1 1 0 1\n", encoding="utf-8")
    assert detect_yolo_mode(labels) == "seg"

    (labels / "2.txt").write_text("0 0 0 1 0 1 1 0 1\n", encoding="utf-8")
    assert detect_yolo_mode(labels) == "obb"

    (labels / "3.txt").write_text("0 0 0 1 0 1 1 0 1\n", encoding="utf-8")
    assert detect_yolo_mode(labels) == "obb"

    (labels / "0.txt").write_text(
        "0 0.1 0.1 0.8 0.8 0.9 0.1\n", encoding="utf-8"
    )
    assert detect_yolo_mode(labels) == "seg"



