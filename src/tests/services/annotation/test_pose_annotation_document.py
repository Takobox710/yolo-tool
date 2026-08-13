from __future__ import annotations

from src.tests.helpers.images import make_image


def test_pose_yolo_labels_load_boxes_points_and_preview(tmp_path):
    from src.services.annotation import load_editable_annotations, load_yolo_annotations, render_annotation_preview

    image_path = make_image(tmp_path / "pose.jpg", size=(100, 100))
    label_path = tmp_path / "pose.txt"
    label_path.write_text(
        "0 0.5 0.5 0.4 0.4 0.4 0.4 2 0.6 0.6 2\n",
        encoding="utf-8",
    )

    editable = load_editable_annotations((100, 100), label_path, task_mode="pose")
    preview_annotations = load_yolo_annotations(
        (100, 100), label_path, "pose", ["person"]
    )

    assert [annotation.shape for annotation in editable] == ["rect", "point", "point"]
    assert preview_annotations[0].keypoints == [(40.0, 40.0), (60.0, 60.0)]
    assert render_annotation_preview(image_path, preview_annotations).size == (100, 100)


def test_yolo_mode_detection_distinguishes_pose_visibility_from_segmentation(tmp_path):
    from src.services.annotation import detect_yolo_mode

    labels = tmp_path / "labels"
    labels.mkdir()
    (labels / "pose.txt").write_text(
        "0 0.5 0.5 0.4 0.4 0.4 0.4 2 0.6 0.6 2\n",
        encoding="utf-8",
    )
    assert detect_yolo_mode(labels) == "pose"

    (labels / "pose.txt").unlink()
    (labels / "seg.txt").write_text(
        "0 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9 1.0\n",
        encoding="utf-8",
    )
    assert detect_yolo_mode(labels) == "seg"
