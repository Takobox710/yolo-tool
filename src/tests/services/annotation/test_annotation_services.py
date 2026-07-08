import json

import os

import sys

from pathlib import Path

from types import SimpleNamespace

import pytest

def make_image(path: Path, size=(100, 100), color="white"):
    from PIL import Image

    Image.new("RGB", size, color).save(path)


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


def test_normalize_ai_target_images_preserves_ui_selected_order_subset(tmp_path):
    from src.services.annotation import normalize_ai_target_images

    images = [tmp_path / f"{index}.jpg" for index in range(1, 5)]

    targets = normalize_ai_target_images(
        images,
        [images[1], images[3], tmp_path / "other.jpg"],
    )

    assert targets == [images[1], images[3]]


def test_annotation_preview_services(tmp_path):
    from src.services.annotation import Annotation, load_yolo_annotations, render_annotation_preview

    image_path = tmp_path / "a.jpg"
    make_image(image_path)
    label = tmp_path / "a.txt"
    label.write_text("0 0.5 0.5 0.2 0.4\n", encoding="utf-8")

    annotations = load_yolo_annotations((100, 100), label, "detect", ["weld"])
    preview = render_annotation_preview(image_path, [Annotation(0, "weld", annotations[0].points)])

    assert annotations[0].points == [(40.0, 30.0), (60.0, 30.0), (60.0, 70.0), (40.0, 70.0)]
    assert preview.size == (100, 100)


def test_annotation_preview_auto_detects_obb_labels(tmp_path):
    from src.services.annotation import load_yolo_annotations, render_annotation_preview

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


def test_annotation_page_labelme_json_roundtrip_and_yolo_export(tmp_path):
    from src.ui.features.annotation.page import (
        EditableAnnotation,
        load_labelme_annotations,
        save_editable_annotations,
        save_labelme_annotations,
    )

    image_path = tmp_path / "a.jpg"
    make_image(image_path)
    json_path = tmp_path / "a.json"
    yolo_path = tmp_path / "a.txt"
    annotations = [
        EditableAnnotation(0, "rect", [(10, 20), (40, 20), (40, 60), (10, 60)]),
        EditableAnnotation(0, "obb_mirror", [(20, 20), (70, 25), (65, 45), (15, 40)]),
    ]

    save_labelme_annotations((100, 100), json_path, image_path, annotations, ["weld"])
    loaded, class_names = load_labelme_annotations((100, 100), json_path, ["weld"])
    save_editable_annotations((100, 100), yolo_path, loaded, "obb")

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["imagePath"] == "a.jpg"
    assert payload["imageWidth"] == 100
    assert [shape["shape_type"] for shape in payload["shapes"]] == [
        "rectangle",
        "oriented_rectangle",
    ]
    assert class_names == ["weld"]
    assert loaded[0].shape == "rect"
    assert loaded[1].shape == "obb"
    assert yolo_path.read_text(encoding="utf-8").splitlines()[0].startswith("0 0.100000")


