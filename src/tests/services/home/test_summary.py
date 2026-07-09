from __future__ import annotations

import csv
import json


def test_build_home_summary_counts_annotations_distribution_and_history(tmp_path):
    from src.services.home import build_home_summary

    images_dir = tmp_path / "images"
    annotations_dir = tmp_path / "annotations"
    labels_dir = tmp_path / "labels"
    dataset_dir = tmp_path / "data"
    result_dir = tmp_path / "result"
    images_dir.mkdir()
    annotations_dir.mkdir()
    labels_dir.mkdir()
    (dataset_dir / "train" / "labels").mkdir(parents=True)
    (dataset_dir / "val" / "labels").mkdir(parents=True)
    (dataset_dir / "test" / "labels").mkdir(parents=True)
    (result_dir / "train-2" / "weights").mkdir(parents=True)

    (images_dir / "1.jpg").write_text("a", encoding="utf-8")
    (images_dir / "2.png").write_text("a", encoding="utf-8")
    (annotations_dir / "1.json").write_text(
        json.dumps({"shapes": [{"label": "weld"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (annotations_dir / "2.json").write_text(
        json.dumps({"shapes": []}, ensure_ascii=False), encoding="utf-8"
    )
    (labels_dir / "1.txt").write_text("0 0.5 0.5 0.2 0.2\n", encoding="utf-8")
    (dataset_dir / "data.yaml").write_text(
        "names: ['weld', 'scratch']\n", encoding="utf-8"
    )
    (dataset_dir / "train" / "labels" / "a.txt").write_text(
        "0 0.5 0.5 0.2 0.2\n1 0.4 0.4 0.1 0.1\n", encoding="utf-8"
    )
    (dataset_dir / "val" / "labels" / "b.txt").write_text(
        "1 0.5 0.5 0.2 0.2\n", encoding="utf-8"
    )
    (result_dir / "train-2" / "weights" / "best.pt").write_text(
        "weights", encoding="utf-8"
    )
    with open(
        result_dir / "train-2" / "results.csv",
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "epoch",
                "time",
                "metrics/mAP50(B)",
                "metrics/mAP50-95(B)",
                "val/box_loss",
                "metrics/recall(B)",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "epoch": 0,
                "time": 10,
                "metrics/mAP50(B)": 0.8,
                "metrics/mAP50-95(B)": 0.6,
                "val/box_loss": 0.2,
                "metrics/recall(B)": 0.7,
            }
        )

    summary = build_home_summary(
        images_dir=images_dir,
        annotations_dir=annotations_dir,
        labels_dir=labels_dir,
        dataset_dir=dataset_dir,
        result_dir=result_dir,
        configured_class_names=["fallback"],
    )

    assert summary["image_count"] == 2
    assert summary["label_count"] == 1
    assert summary["single_counts"] == {"train": 1, "val": 0, "test": 0}
    assert summary["multi_counts"] == {"weld": 1, "scratch": 2}
    assert summary["class_names"] == ["weld", "scratch"]
    assert summary["curve_data"]["epoch"] == [0.0]
    assert len(summary["history_entries"]) == 1
    assert summary["history_entries"][0]["train_id"] == "train-2"
    assert summary["history_entries"][0]["model_name"] == "best.pt"
    assert summary["history_entries"][0]["metrics"]["map50"] == "80.0%"


def test_build_home_summary_falls_back_to_yolo_labels_when_no_valid_json(tmp_path):
    from src.services.home import build_home_summary

    images_dir = tmp_path / "images"
    annotations_dir = tmp_path / "annotations"
    labels_dir = tmp_path / "labels"
    dataset_dir = tmp_path / "data"
    result_dir = tmp_path / "result"
    images_dir.mkdir()
    annotations_dir.mkdir()
    labels_dir.mkdir()
    dataset_dir.mkdir()
    result_dir.mkdir()

    (annotations_dir / "1.json").write_text("{}", encoding="utf-8")
    (labels_dir / "1.txt").write_text("0 0.5 0.5 0.2 0.2\n", encoding="utf-8")
    (labels_dir / "2.txt").write_text("\n", encoding="utf-8")

    summary = build_home_summary(
        images_dir=images_dir,
        annotations_dir=annotations_dir,
        labels_dir=labels_dir,
        dataset_dir=dataset_dir,
        result_dir=result_dir,
        configured_class_names=["weld"],
    )

    assert summary["label_count"] == 1
    assert summary["single_counts"] == {"train": 0, "val": 0, "test": 0}
    assert summary["multi_counts"] == {"weld": 0}
