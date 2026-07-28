from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


def _mask(x1: int, y1: int, x2: int, y2: int) -> np.ndarray:
    value = np.zeros((48, 64), dtype=np.uint8)
    value[y1:y2, x1:x2] = 1
    return value


def test_sam3_checkpoint_discovery_prioritizes_project(tmp_path):
    from src.services.annotation.sam3_text import find_sam3_model_paths

    project = tmp_path / "project"
    app = tmp_path / "app"
    (project / "data" / "models").mkdir(parents=True)
    (app / "data" / "models").mkdir(parents=True)
    (project / "data" / "models" / "sam3.pt").write_bytes(b"project")
    (app / "data" / "models" / "sam3.pt").write_bytes(b"app")

    paths = find_sam3_model_paths(project, app)

    assert paths == [(project / "data" / "models" / "sam3.pt").resolve()]


def test_sam3_prompt_normalization_defaults_to_class_names():
    from src.services.annotation.sam3_text import normalize_sam3_prompts

    assert normalize_sam3_prompts(["weld", "scratch"], {}, []) == [
        (0, "weld", "weld"),
        (1, "scratch", "scratch"),
    ]
    assert normalize_sam3_prompts(
        ["weld", "scratch"], {"weld": "a weld seam"}, ["weld"]
    ) == [(0, "weld", "a weld seam")]


def test_sam3_shape_conversion_and_stable_overlap_dedup():
    from src.services.annotation.sam3_text import (
        _deduplicate_candidates,
        sam3_annotations_from_masks,
    )

    first, _ = sam3_annotations_from_masks(
        [_mask(8, 8, 28, 30)], [0.91], 0, "obb", 4, 0.002, 0
    )
    second, _ = sam3_annotations_from_masks(
        [_mask(9, 9, 27, 29)], [0.80], 1, "polygon", 4, 0.002, 1
    )
    accepted, filtered = _deduplicate_candidates(first + second, 0.80)

    assert len(first[0].points) == 4
    assert len(second[0].points) == 4
    assert [item.class_id for item in accepted] == [0]
    assert filtered == 1


def test_sam3_minimum_area_counts_mask_pixels():
    from src.services.annotation.sam_assist import sam_geometry_from_mask

    mask = np.zeros((8, 8), dtype=np.uint8)
    mask[2:4, 2:4] = 1

    assert sam_geometry_from_mask(mask, 0.8, minimum_area=4) is not None
    assert sam_geometry_from_mask(mask, 0.8, minimum_area=5) is None


def test_sam3_prediction_encodes_each_image_once_for_multiple_prompts(tmp_path):
    from src.services.annotation.ai_labeling import predict_sam3_annotations_for_image

    image_path = tmp_path / "image.jpg"
    Image.new("RGB", (64, 48), "white").save(image_path)

    class FakeRuntime:
        def __init__(self):
            self.set_image_calls = 0
            self.prompts: list[str] = []

        def set_image(self, path: Path):
            self.set_image_calls += 1
            assert path == image_path

        def predict_prompt(self, prompt: str, confidence: float):
            self.prompts.append(prompt)
            offset = 8 if prompt == "weld seam" else 32
            return [_mask(offset, 8, offset + 12, 24)], [confidence + 0.2]

    runtime = FakeRuntime()
    annotations, stats = predict_sam3_annotations_for_image(
        image_path,
        runtime,
        0.5,
        0.8,
        "rect",
        {"weld": "weld seam", "scratch": "scratch"},
        ["weld", "scratch"],
        ["weld", "scratch"],
        4,
        0.002,
    )

    assert runtime.set_image_calls == 1
    assert runtime.prompts == ["weld seam", "scratch"]
    assert [item.class_id for item in annotations] == [0, 1]
    assert all(item.shape == "rect" for item in annotations)
    assert stats == {"raw_count": 2, "area_filtered": 0, "overlap_filtered": 0}


def test_apply_ai_labeling_accepts_sam3_backend_and_writes_shapes(tmp_path):
    from src.services.annotation.ai_labeling import apply_ai_labeling
    from src.services.annotation.editable_document import (
        save_editable_annotations,
        save_labelme_annotations,
    )
    from threading import Event

    image_path = tmp_path / "image.jpg"
    Image.new("RGB", (64, 48), "white").save(image_path)
    annotations_dir = tmp_path / "annotations"
    labels_dir = tmp_path / "labels"

    class FakeRuntime:
        def set_image(self, _path):
            pass

        def predict_prompt(self, _prompt, _confidence):
            return [_mask(8, 8, 28, 30)], [0.95]

    result = apply_ai_labeling(
        image_items=[image_path],
        current_image=image_path,
        annotations_dir=annotations_dir,
        labels_dir=labels_dir,
        model_path=str(tmp_path / "sam3.pt"),
        backend="sam3",
        confidence=0.5,
        iou=0.8,
        imgsz=640,
        range_mode="当前图片",
        process_mode="替换",
        class_mapping={},
        class_names=["weld"],
        line_expand_pixels=10,
        save_json_fn=save_labelme_annotations,
        save_yolo_fn=save_editable_annotations,
        output_mode="detect",
        auto_convert_yolo=False,
        sam3_prompts={"weld": "weld seam"},
        sam3_enabled_classes=["weld"],
        sam3_output_shape="polygon",
        progress_callback=lambda _payload: None,
        stop_event=Event(),
        model=FakeRuntime(),
    )

    assert result.processed == 1
    payload = (annotations_dir / "image.json").read_text(encoding="utf-8")
    assert '"shape_type": "polygon"' in payload


def test_sam3_polygon_becomes_minimum_area_obb_for_obb_yolo_output(tmp_path):
    from threading import Event

    from src.services.annotation.ai_labeling import apply_ai_labeling
    from src.services.annotation.editable_document import (
        save_editable_annotations,
        save_labelme_annotations,
    )

    image_path = tmp_path / "image.jpg"
    Image.new("RGB", (64, 48), "white").save(image_path)
    annotations_dir = tmp_path / "annotations"
    labels_dir = tmp_path / "labels"

    class FakeRuntime:
        def set_image(self, _path):
            pass

        def predict_prompt(self, _prompt, _confidence):
            mask = np.zeros((48, 64), dtype=np.uint8)
            mask[10:36, 18:48] = 1
            return [mask], [0.9]

    apply_ai_labeling(
        image_items=[image_path],
        current_image=image_path,
        annotations_dir=annotations_dir,
        labels_dir=labels_dir,
        model_path=str(tmp_path / "sam3.pt"),
        backend="sam3",
        confidence=0.5,
        iou=0.8,
        imgsz=640,
        range_mode="当前图片",
        process_mode="替换",
        class_mapping={},
        class_names=["weld"],
        line_expand_pixels=10,
        save_json_fn=save_labelme_annotations,
        save_yolo_fn=save_editable_annotations,
        output_mode="obb",
        auto_convert_yolo=True,
        sam3_prompts={"weld": "weld"},
        sam3_enabled_classes=["weld"],
        sam3_output_shape="polygon",
        progress_callback=lambda _payload: None,
        stop_event=Event(),
        model=FakeRuntime(),
    )

    values = (labels_dir / "image.txt").read_text(encoding="utf-8").split()
    assert len(values) == 9
    points = [float(value) for value in values[1:]]
    assert len(points) == 8
    assert max(points[::2]) - min(points[::2]) > 0
    assert max(points[1::2]) - min(points[1::2]) > 0
