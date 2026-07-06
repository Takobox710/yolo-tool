import json

import os

import sys

from pathlib import Path

from types import SimpleNamespace

import pytest

def make_image(path: Path, size=(100, 100), color="white"):
    from PIL import Image

    Image.new("RGB", size, color).save(path)


def test_rename_preview_execute_and_conflict(tmp_path):
    from scr.services.rename_service import execute_rename, preview_rename

    (tmp_path / "a.jpg").write_bytes(b"a")
    plan = preview_rename(tmp_path, "W", 1, 2)
    result = execute_rename(plan)
    assert result.renamed_count == 1
    assert (tmp_path / "W01.jpg").exists()

    (tmp_path / "b.jpg").write_bytes(b"b")
    conflict_plan = preview_rename(tmp_path, "W", 1, 2)
    assert conflict_plan[0].conflict is True


def test_rename_preview_uses_natural_numeric_sort(tmp_path):
    from scr.services.rename_service import preview_rename

    for name in ["1.jpg", "10.jpg", "100.jpg", "2.jpg", "3.jpg"]:
        (tmp_path / name).write_bytes(b"image")

    plan = preview_rename(tmp_path, "", 1, 1)

    assert [item.old_name for item in plan] == ["1.jpg", "2.jpg", "3.jpg", "10.jpg", "100.jpg"]
    assert [item.new_name for item in plan] == ["1.jpg", "2.jpg", "3.jpg", "4.jpg", "5.jpg"]


def test_rename_can_include_matching_labels_and_blocks_label_conflicts(tmp_path):
    from scr.services.rename_service import execute_rename, preview_rename

    images = tmp_path / "images"
    labels = tmp_path / "labels"
    images.mkdir()
    labels.mkdir()
    (images / "2.jpg").write_bytes(b"image")
    (labels / "1.txt").write_text("old", encoding="utf-8")
    (labels / "2.txt").write_text("match", encoding="utf-8")

    blocked = preview_rename(images, "", 1, 1, labels_dir=labels, include_labels=True)
    assert blocked[0].label_conflict is True
    assert execute_rename(blocked).renamed_count == 0
    assert (images / "2.jpg").exists()
    assert (labels / "2.txt").exists()

    (labels / "1.txt").unlink()
    plan = preview_rename(images, "A", 1, 1, labels_dir=labels, include_labels=True)
    assert plan[0].conflict is False
    assert plan[0].label_target == labels / "A1.txt"
    result = execute_rename(plan)
    assert result.renamed_count == 1
    assert result.label_renamed_count == 1
    assert (images / "A1.jpg").exists()
    assert (labels / "A1.txt").read_text(encoding="utf-8") == "match"


def test_rename_can_include_labelme_and_yolo_labels_separately(tmp_path):
    from scr.services.rename_service import execute_rename, preview_rename

    images = tmp_path / "images"
    labelme = tmp_path / "labelme"
    yolo = tmp_path / "yolo"
    images.mkdir()
    labelme.mkdir()
    yolo.mkdir()
    (images / "2.jpg").write_bytes(b"image")
    (labelme / "2.json").write_text("labelme", encoding="utf-8")
    (yolo / "2.txt").write_text("yolo", encoding="utf-8")

    plan = preview_rename(
        images,
        "A",
        1,
        1,
        labelme_dir=labelme,
        include_labelme=True,
        labels_dir=yolo,
        include_labels=True,
    )

    assert plan[0].labelme_source == labelme / "2.json"
    assert plan[0].labelme_target == labelme / "A1.json"
    assert plan[0].label_source == yolo / "2.txt"
    assert plan[0].label_target == yolo / "A1.txt"
    result = execute_rename(plan)
    assert result.renamed_count == 1
    assert result.labelme_renamed_count == 1
    assert result.label_renamed_count == 1
    assert (images / "A1.jpg").exists()
    assert (labelme / "A1.json").read_text(encoding="utf-8") == "labelme"
    assert (yolo / "A1.txt").read_text(encoding="utf-8") == "yolo"
