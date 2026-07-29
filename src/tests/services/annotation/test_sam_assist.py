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
    (app_models / "sam3.pt").write_bytes(b"sam3")
    (app_models / "SAM_custom_weld.pt").write_bytes(b"custom")
    (app_models / "other.pt").write_bytes(b"other")

    specs = find_sam_model_specs(project_root, app_root)

    assert [spec.key for spec in specs] == [
        "sam2.1_hiera_base_plus.pt",
        "sam2_hiera_tiny.pt",
        "sam3.pt",
        "SAM_custom_weld.pt",
    ]
    assert specs[0].checkpoint_path.parent == project_models.resolve()
    assert specs[0].config_name == "configs/sam2.1/sam2.1_hiera_b+.yaml"
    assert specs[1].config_name == "configs/sam2/sam2_hiera_t.yaml"
    assert specs[2].display_name == "SAM 3"
    assert specs[2].runtime_kind == "sam3"
    assert specs[3].display_name == "SAM_custom_weld.pt"
    assert specs[3].runtime_kind == "unknown"
    assert sam_model_spec_from_path(app_models / "other.pt") is None


def test_sam_model_catalog_simplifies_known_sam_versions_and_sizes(tmp_path):
    from src.services.annotation.sam_assist import sam_model_spec_from_path

    expected = {
        "sam2.1_hiera_small.pt": "SAM 2.1 Small",
        "sam2_hiera_large.pt": "SAM 2 Large",
        "sam_vit_h_4b8939.pt": "SAM ViT-H",
    }
    for filename, display_name in expected.items():
        spec = sam_model_spec_from_path(tmp_path / filename)
        assert spec is not None
        assert spec.display_name == display_name


def test_sam3_canvas_runtime_forwards_point_prompt(monkeypatch):
    from src.services.annotation.sam_runtime import _Sam3CanvasRuntime

    calls = {}

    class FakeTorch:
        @staticmethod
        def inference_mode():
            return nullcontext()

        @staticmethod
        def autocast(**_kwargs):
            return nullcontext()

    class FakeModel:
        def predict_inst(self, state, **kwargs):
            calls["state"] = state
            calls.update(kwargs)
            mask = np.zeros((32, 32), dtype=np.uint8)
            mask[8:24, 10:22] = 1
            return np.asarray([mask]), np.asarray([0.88]), np.zeros((1, 8, 8))

    monkeypatch.setitem(__import__("sys").modules, "torch", FakeTorch)
    runtime = _Sam3CanvasRuntime()
    runtime.model = FakeModel()
    runtime.state = {"original_height": 32, "original_width": 32}

    masks, scores = runtime.predict_point(12.0, 15.0, multimask_output=False)

    assert calls["state"] == runtime.state
    assert calls["point_coords"].tolist() == [[12.0, 15.0]]
    assert calls["point_labels"].tolist() == [1]
    assert calls["multimask_output"] is False
    assert masks.shape == (1, 32, 32)
    assert scores.tolist() == [0.88]


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


def test_sam_runtime_selects_best_candidate_and_applies_advanced_filters(monkeypatch):
    from src.services.annotation.sam_runtime import SamAssistRuntime

    class FakePredictor:
        def predict(self, **kwargs):
            assert kwargs["multimask_output"] is True
            small = np.zeros((40, 40), dtype=np.uint8)
            small[2:4, 2:4] = 1
            best = np.zeros((40, 40), dtype=np.uint8)
            best[8:30, 10:32] = 1
            return (
                np.asarray([small, best]),
                np.asarray([0.4, 0.9]),
                np.zeros((2, 8, 8)),
            )

    fake_torch = SimpleNamespace(inference_mode=lambda: nullcontext())
    monkeypatch.setitem(__import__("sys").modules, "torch", fake_torch)
    runtime = SamAssistRuntime()
    runtime.predictor = FakePredictor()
    runtime.runtime_kind = "sam2"
    runtime.device = "cpu"
    runtime.model_generation = 3
    runtime.image_generation = 5
    runtime.image_path = "image.jpg"

    result = runtime.predict_point(
        12.0,
        15.0,
        5,
        3,
        True,
        0.8,
        10,
        0.01,
    )
    filtered = runtime.predict_point(12.0, 15.0, 5, 3, True, 0.95, 10, 0.01)

    assert result["geometry"]["score"] == 0.9
    assert result["geometry"]["rectangle"] == [
        [10.0, 8.0],
        [32.0, 8.0],
        [32.0, 30.0],
        [10.0, 30.0],
    ]
    assert filtered["geometry"] is None


def test_sam3_canvas_runtime_requires_cuda(tmp_path, monkeypatch):
    from src.services.annotation.sam_runtime import _Sam3CanvasRuntime

    checkpoint = tmp_path / "sam3.pt"
    checkpoint.write_bytes(b"sam3")
    fake_torch = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False))
    monkeypatch.setitem(__import__("sys").modules, "torch", fake_torch)

    with __import__("pytest").raises(RuntimeError, match="需要 CUDA GPU"):
        _Sam3CanvasRuntime().load_model(checkpoint)


def test_sam_runtime_uses_sam3_interactive_candidates():
    from src.services.annotation.sam_runtime import SamAssistRuntime

    calls = {}

    class FakeSam3Runtime:
        def predict_point(self, x, y, *, multimask_output):
            calls.update(x=x, y=y, multimask_output=multimask_output)
            mask = np.zeros((24, 24), dtype=np.uint8)
            mask[4:20, 5:18] = 1
            return np.asarray([mask]), np.asarray([0.85])

    runtime = SamAssistRuntime()
    runtime.runtime_kind = "sam3"
    runtime.sam3_runtime = FakeSam3Runtime()
    runtime.model_generation = 7
    runtime.image_generation = 9
    runtime.image_path = "image.jpg"

    result = runtime.predict_point(8.0, 9.0, 9, 7, True, 0.5, 4, 0.002)

    assert calls == {"x": 8.0, "y": 9.0, "multimask_output": True}
    assert result["geometry"]["score"] == 0.85
