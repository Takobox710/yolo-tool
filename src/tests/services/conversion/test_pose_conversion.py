from __future__ import annotations

import json

import pytest

from src.tests.helpers.images import make_image


def _config(tmp_path):
    from src.services.conversion import ConversionConfig

    return ConversionConfig(
        task_mode="pose",
        images_dir=tmp_path / "images",
        annotations_dir=tmp_path / "images",
        output_dir=tmp_path / "dataset",
        labels_dir=tmp_path / "labels",
        class_names=["person"],
        train_ratio=1.0,
        val_ratio=0.0,
        test_ratio=0.0,
    )


def test_pose_conversion_pairs_same_class_points_and_writes_kpt_shape(tmp_path):
    images = tmp_path / "images"
    images.mkdir()
    make_image(images / "person.jpg", size=(100, 100))
    (images / "person.json").write_text(
        json.dumps(
            {
                "imageWidth": 100,
                "imageHeight": 100,
                "shapes": [
                    {"label": "person", "shape_type": "rectangle", "points": [[10, 10], [90, 90]]},
                    {"label": "person", "shape_type": "point", "points": [[25, 30]]},
                    {"label": "person", "shape_type": "point", "points": [[70, 75]]},
                ],
            }
        ),
        encoding="utf-8",
    )

    from src.services.conversion import run_conversion

    result = run_conversion(_config(tmp_path))
    label_text = (tmp_path / "dataset" / "train" / "labels" / "person.txt").read_text(encoding="utf-8")
    assert label_text.strip() == "0 0.500000 0.500000 0.800000 0.800000 0.250000 0.300000 2 0.700000 0.750000 2"
    assert result.keypoint_count == 2
    assert "kpt_shape: [2, 3]" in (tmp_path / "dataset" / "data.yaml").read_text(encoding="utf-8")


def test_pose_preview_reports_invalid_point_without_writing(tmp_path):
    images = tmp_path / "images"
    images.mkdir()
    make_image(images / "bad.jpg", size=(100, 100))
    (images / "bad.json").write_text(
        json.dumps(
            {
                "imageWidth": 100,
                "imageHeight": 100,
                "shapes": [
                    {"label": "person", "shape_type": "rectangle", "points": [[10, 10], [40, 40]]},
                    {"label": "person", "shape_type": "point", "points": [[80, 80]]},
                ],
            }
        ),
        encoding="utf-8",
    )
    config = _config(tmp_path)

    from src.services.conversion import preview_conversion, run_conversion

    preview = preview_conversion(config)
    assert "bad.json" in preview.invalid_images
    with pytest.raises(ValueError, match="未写入任何文件"):
        run_conversion(config)
    assert not (tmp_path / "dataset").exists()


def test_pose_conversion_rejects_inconsistent_keypoint_counts(tmp_path):
    images = tmp_path / "images"
    images.mkdir()
    make_image(images / "mismatch.jpg", size=(100, 100))
    (images / "mismatch.json").write_text(
        json.dumps(
            {
                "imageWidth": 100,
                "imageHeight": 100,
                "shapes": [
                    {"label": "person", "shape_type": "rectangle", "points": [[0, 0], [40, 40]]},
                    {"label": "person", "shape_type": "rectangle", "points": [[60, 60], [100, 100]]},
                    {"label": "person", "shape_type": "point", "points": [[10, 10]]},
                    {"label": "person", "shape_type": "point", "points": [[20, 20]]},
                    {"label": "person", "shape_type": "point", "points": [[70, 70]]},
                ],
            }
        ),
        encoding="utf-8",
    )

    from src.services.conversion import preview_conversion

    preview = preview_conversion(_config(tmp_path))
    assert "mismatch.json" in preview.invalid_images
    assert "数量必须一致" in preview.invalid_images["mismatch.json"]
