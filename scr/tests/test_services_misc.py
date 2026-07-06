import json

import os

import sys

from pathlib import Path

from types import SimpleNamespace

import pytest

def make_image(path: Path, size=(100, 100), color="white"):
    from PIL import Image

    Image.new("RGB", size, color).save(path)


def test_validation_model_choices_include_result_best_and_optional_last(tmp_path):
    from scr.services.detection_service import find_result_model_paths

    run_dir = tmp_path / "result" / "train-2" / "weights"
    run_dir.mkdir(parents=True)
    (run_dir / "best.pt").write_text("best", encoding="utf-8")
    (run_dir / "last.pt").write_text("last", encoding="utf-8")

    with_last = find_result_model_paths(tmp_path / "result", show_last_training_models=True)
    without_last = find_result_model_paths(
        tmp_path / "result", show_last_training_models=False
    )

    assert [path.name for path in with_last] == ["best.pt", "last.pt"]
    assert [path.name for path in without_last] == ["best.pt"]
