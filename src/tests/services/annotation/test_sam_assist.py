from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import numpy as np


def test_sam_model_catalog_recognizes_variants_and_project_priority(tmp_path):
    from src.services.annotation import find_sam_model_specs
    from src.services.annotation.sam_assist import sam_model_spec_from_path

    project_root = tmp_path / "project"
    app_root = tmp_path / "app"
    project_models = project_root / "data" / "models"
    app_models = app_root / "data" / "models"
    project_models.mkdir(parents=True)
    app_models.mkdir(parents=True)
    (project_models / "sam2.1_hiera_base_plus.pt").write_bytes(b"project")
    (app_models / "sam2.1_hiera_base_plus.pt").write_bytes(b"app")
    (app_models / "sam2_hiera_tiny.pt").write_bytes(b"tiny")
    (app_models / "other.pt").write_bytes(b"other")

    specs = find_sam_model_specs(project_root, app_root)

    assert [spec.key for spec in specs] == [
        "sam2.1_hiera_base_plus.pt",
        "sam2_hiera_tiny.pt",
    ]
    assert specs[0].checkpoint_path.parent == project_models.resolve()
    assert specs[0].config_name == "configs/sam2.1/sam2.1_hiera_b+.yaml"
    assert specs[1].config_name == "configs/sam2/sam2_hiera_t.yaml"
    assert sam_model_spec_from_path(app_models / "other.pt") is None


def test_preferred_sam_model_restores_saved_then_base_plus(tmp_path):
    from src.services.annotation import preferred_sam_model
    from src.services.annotation.sam_assist import sam_model_spec_from_path

    paths = [
        tmp_path / "sam2.1_hiera_tiny.pt",
        tmp_path / "sam2.1_hiera_base_plus.pt",
    ]
    specs = [sam_model_spec_from_path(path) for path in paths]
    specs = [spec for spec in specs if spec is not None]

    assert preferred_sam_model(specs, "sam2.1_hiera_tiny.pt").key.endswith("tiny.pt")
    assert preferred_sam_model(specs, "").key.endswith("base_plus.pt")


def test_sam_geometry_converts_largest_mask_contour():
    from src.services.annotation.sam_assist import sam_geometry_from_mask

    mask = np.zeros((80, 100), dtype=np.uint8)
    mask[20:60, 30:75] = 1
    mask[2:4, 2:4] = 1

    geometry = sam_geometry_from_mask(mask, 0.91)

    assert geometry is not None
    assert geometry.score == 0.91
    assert len(geometry.polygon) == 4
    assert geometry.rectangle == [
        (30.0, 20.0),
        (75.0, 20.0),
        (75.0, 60.0),
        (30.0, 60.0),
    ]
    assert len(geometry.oriented_rectangle) == 4


def test_sam_geometry_rejects_empty_and_tiny_masks():
    from src.services.annotation.sam_assist import sam_geometry_from_mask

    assert sam_geometry_from_mask(np.zeros((16, 16), dtype=np.uint8), 0.5) is None
    tiny = np.zeros((16, 16), dtype=np.uint8)
    tiny[2:4, 2:4] = 1
    assert sam_geometry_from_mask(tiny, 0.5, minimum_area=10) is None


def test_sam_runtime_predicts_with_single_positive_point(monkeypatch):
    from src.services.annotation.sam_runtime import SamAssistRuntime

    calls = {}

    class FakePredictor:
        def predict(self, **kwargs):
            calls.update(kwargs)
            mask = np.zeros((32, 32), dtype=np.uint8)
            mask[8:24, 10:22] = 1
            return np.asarray([mask]), np.asarray([0.88]), np.zeros((1, 8, 8))

    fake_torch = SimpleNamespace(inference_mode=lambda: nullcontext())
    monkeypatch.setitem(__import__("sys").modules, "torch", fake_torch)
    runtime = SamAssistRuntime()
    runtime.predictor = FakePredictor()
    runtime.device = "cpu"
    runtime.model_generation = 4
    runtime.image_generation = 7
    runtime.image_path = "image.jpg"

    result = runtime.predict_point(12.0, 15.0, 7, 4)

    assert calls["point_coords"].tolist() == [[12.0, 15.0]]
    assert calls["point_labels"].tolist() == [1]
    assert calls["multimask_output"] is False
    assert result["geometry"] is not None
