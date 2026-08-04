"""Fixtures shared by model-export service workflow tests."""

import pytest


@pytest.fixture
def model_export_config(tmp_path):
    from src.services.model_export import ModelExportConfig

    def factory(**overrides):
        values = {
            "model_path": tmp_path / "model.pt",
            "output_dir": tmp_path / "output",
            "export_format": "onnx",
        }
        values.update(overrides)
        return ModelExportConfig(**values)

    return factory
