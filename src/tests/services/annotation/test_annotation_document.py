import json

import os

import sys

from pathlib import Path

from types import SimpleNamespace

import pytest

def make_image(path: Path, size=(100, 100), color="white"):
    from PIL import Image

    Image.new("RGB", size, color).save(path)


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



def test_annotation_preview_loads_segmentation_polygon(tmp_path):
    from src.services.annotation import load_yolo_annotations

    label = tmp_path / "seg.txt"
    label.write_text("0 0.1 0.2 0.8 0.2 0.8 0.9\n", encoding="utf-8")

    annotations = load_yolo_annotations((100, 100), label, "seg", ["weld"])

    assert annotations[0].points == [(10.0, 20.0), (80.0, 20.0), (80.0, 90.0)]



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



def test_seg_yolo_roundtrip_loads_polygons_and_converts_circles(tmp_path):
    from src.services.annotation import (
        EditableAnnotation,
        load_editable_annotations,
        save_editable_annotations,
    )

    label_path = tmp_path / "seg.txt"
    label_path.write_text(
        "2 0.100000 0.200000 0.800000 0.200000 0.800000 0.900000\n",
        encoding="utf-8",
    )

    loaded = load_editable_annotations((100, 100), label_path, task_mode="seg")

    assert loaded[0].shape == "polygon"
    assert loaded[0].class_id == 2
    assert loaded[0].points == [(10.0, 20.0), (80.0, 20.0), (80.0, 90.0)]

    circle = EditableAnnotation(
        1,
        "circle",
        [(25.0, 25.0), (75.0, 25.0), (75.0, 75.0), (25.0, 75.0)],
        radius_point=(75.0, 50.0),
    )
    save_editable_annotations((100, 100), label_path, [circle], "seg")
    values = label_path.read_text(encoding="utf-8").strip().split()

    assert values[0] == "1"
    assert len(values[1:]) == 64



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



