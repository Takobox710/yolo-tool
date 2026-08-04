import json

import os

import sys

from types import SimpleNamespace

import pytest

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

