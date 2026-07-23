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
    assert payload["shapes"][1]["flags"]["yolo_tool_shape"] == "obb_mirror"
    assert class_names == ["weld"]
    assert loaded[0].shape == "rect"
    assert loaded[1].shape == "obb_mirror"
    assert yolo_path.read_text(encoding="utf-8").splitlines()[0].startswith("0 0.100000")


def test_labelme_line_loads_as_mirror_obb(tmp_path):
    from src.services.annotation import load_labelme_annotations

    json_path = tmp_path / "line.json"
    json_path.write_text(
        json.dumps(
            {
                "imageWidth": 100,
                "imageHeight": 100,
                "shapes": [
                    {
                        "label": "weld",
                        "shape_type": "line",
                        "points": [[20, 50], [80, 50]],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    annotations, _class_names = load_labelme_annotations(
        (100, 100), json_path, [], line_expand_pixels=10
    )

    assert annotations[0].shape == "obb_mirror"


def test_load_labelme_annotations_keeps_empty_initial_class_list(tmp_path):
    from src.services.annotation import load_labelme_annotations

    annotations, class_names = load_labelme_annotations(
        (100, 100), tmp_path / "missing.json", []
    )

    assert annotations == []
    assert class_names == []


def test_circle_labelme_roundtrip_preserves_radius_point_direction(tmp_path):
    from src.services.annotation import (
        EditableAnnotation,
        load_labelme_annotations,
        save_labelme_annotations,
    )

    image_path = tmp_path / "circle.jpg"
    make_image(image_path)
    json_path = tmp_path / "circle.json"
    circle = EditableAnnotation(
        0,
        "circle",
        [
            (30.20101012677667, 30.20101012677667),
            (69.79898987322333, 30.20101012677667),
            (69.79898987322333, 69.79898987322333),
            (30.20101012677667, 69.79898987322333),
        ],
        radius_point=(64.0, 64.0),
    )

    save_labelme_annotations((100, 100), json_path, image_path, [circle], ["weld"])
    loaded, _ = load_labelme_annotations((100, 100), json_path, ["weld"])
    payload = json.loads(json_path.read_text(encoding="utf-8"))

    assert payload["shapes"][0]["points"] == [[50.0, 50.0], [64.0, 64.0]]
    assert loaded[0].radius_point == (64.0, 64.0)


def test_collect_labelme_class_names_appends_project_labels(tmp_path):
    from src.services.annotation import collect_labelme_class_names

    annotations_dir = tmp_path / "annotations"
    annotations_dir.mkdir()
    (annotations_dir / "1.json").write_text(
        json.dumps(
            {"shapes": [{"label": "weld"}, {"label": "scratch"}, {"label": ""}]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (annotations_dir / "2.json").write_text(
        json.dumps({"shapes": [{"label": "weld"}, {"label": "crack"}]}, ensure_ascii=False),
        encoding="utf-8",
    )

    assert collect_labelme_class_names(annotations_dir, ["configured"]) == [
        "configured",
        "weld",
        "scratch",
        "crack",
    ]


def test_labelme_class_counts_and_conversion_cover_all_project_files(tmp_path):
    from src.services.annotation import (
        collect_labelme_class_counts,
        convert_labelme_classes,
    )

    annotations_dir = tmp_path / "annotations"
    annotations_dir.mkdir()
    first = annotations_dir / "1.json"
    second = annotations_dir / "2.json"
    first.write_text(
        json.dumps({"shapes": [{"label": "weld"}, {"label": "weld"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    second.write_text(
        json.dumps({"shapes": [{"label": "weld"}, {"label": "scratch"}]}, ensure_ascii=False),
        encoding="utf-8",
    )

    assert collect_labelme_class_counts(annotations_dir, ["weld", "scratch"]) == [3, 1]
    assert convert_labelme_classes(annotations_dir, "weld", "scratch") == 3
    assert collect_labelme_class_counts(annotations_dir, ["weld", "scratch"]) == [0, 4]
