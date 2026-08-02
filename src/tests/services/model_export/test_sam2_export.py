from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest


def _write_fixture(path: Path, input_names: list[str], output_names: list[str]) -> None:
    import onnx
    from onnx import TensorProto, helper

    if path.name == "image_encoder.onnx":
        inputs = [
            helper.make_tensor_value_info(
                "image", TensorProto.FLOAT, [1, 3, 1024, 1024]
            )
        ]
        outputs = [
            helper.make_tensor_value_info(name, TensorProto.FLOAT, [1, 1, 1, 1])
            for name in output_names
        ]
        nodes = [
            helper.make_node(
                "Constant",
                [],
                [name],
                value=helper.make_tensor(
                    f"{name}_value", TensorProto.FLOAT, [1, 1, 1, 1], [0.0]
                ),
            )
            for name in output_names
        ]
    else:
        inputs = [
            helper.make_tensor_value_info(
                "image_embed", TensorProto.FLOAT, [1, 1, 1, 1]
            ),
            helper.make_tensor_value_info(
                "high_res_0", TensorProto.FLOAT, [1, 1, 1, 1]
            ),
            helper.make_tensor_value_info(
                "high_res_1", TensorProto.FLOAT, [1, 1, 1, 1]
            ),
            helper.make_tensor_value_info("point_coords", TensorProto.FLOAT, [1, 1, 2]),
            helper.make_tensor_value_info("point_labels", TensorProto.INT32, [1, 1]),
        ]
        outputs = [
            helper.make_tensor_value_info(name, TensorProto.FLOAT, [1, 1, 1, 1])
            for name in output_names
        ]
        nodes = [
            helper.make_node("Identity", [input_name], [output_name])
            for input_name, output_name in zip(input_names[:3], output_names)
        ]
    graph = helper.make_graph(nodes, "sam2-fixture", inputs, outputs)
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
    model.ir_version = 10
    path.parent.mkdir(parents=True, exist_ok=True)
    onnx.save(model, path)


def test_sam2_image_tensor_matches_predictor_normalization(tmp_path):
    import numpy as np
    from PIL import Image

    from src.services.model_export.calibration import load_sam2_image_tensor

    image = tmp_path / "pixel.png"
    Image.new("RGB", (1, 1), color=(255, 128, 0)).save(image)
    tensor = load_sam2_image_tensor(image, height=1, width=1)

    expected = np.asarray(
        [
            (1.0 - 0.485) / 0.229,
            ((128.0 / 255.0) - 0.456) / 0.224,
            (0.0 - 0.406) / 0.225,
        ],
        dtype=np.float32,
    )
    np.testing.assert_allclose(tensor[0, :, 0, 0], expected, rtol=1e-6, atol=1e-6)


@pytest.mark.parametrize("precision", ["fp32", "fp16"])
def test_sam2_export_writes_fixed_two_file_artifact(monkeypatch, tmp_path, precision):
    import torch

    from src.services.model_export import sam_onnx

    source = tmp_path / "sam2.1_hiera_base_plus.pt"
    source.write_bytes(b"checkpoint")
    calibration_dir = tmp_path / "calibration"
    calibration_dir.mkdir()
    from PIL import Image

    Image.new("RGB", (8, 8), color="white").save(calibration_dir / "one.png")

    class FakeModel:
        def parameters(self):
            yield torch.zeros(1)

    class FakeEncoderWrapper:
        def __init__(self, _model):
            self.module = self

        def eval(self):
            return self

        def __call__(self, _image):
            return (
                torch.zeros(1, 1, 1, 1),
                torch.zeros(1, 1, 1, 1),
                torch.zeros(1, 1, 1, 1),
            )

    class FakeDecoderWrapper:
        def __init__(self, _model):
            self.module = self

        def eval(self):
            return self

    def fake_export(_module, _args, target, input_names, output_names, **_kwargs):
        _write_fixture(Path(target), input_names, output_names)

    quantize_calls = []
    monkeypatch.setattr(
        sam_onnx,
        "_load_sam2_model",
        lambda _path: (FakeModel(), SimpleNamespace(config_name="sam2/config.yaml")),
    )
    monkeypatch.setattr(sam_onnx, "_Sam2ImageEncoderWrapper", FakeEncoderWrapper)
    monkeypatch.setattr(sam_onnx, "_Sam2MaskDecoderWrapper", FakeDecoderWrapper)
    monkeypatch.setattr(sam_onnx, "_export_onnx", fake_export)

    options = {
        "model": str(source),
        "format": "onnx",
        "precision": precision,
        "simplify": False,
        "output_dir": str(tmp_path / "exports"),
        "calibration_data": str(calibration_dir),
        "calibration_samples": 1,
        "validate_quantized": False,
    }
    result = sam_onnx.export_sam2_model_to_directory(options)

    assert result.name == f"sam2.1_hiera_base_plus_sam2_onnx_{precision}"
    assert (result / "image_encoder.onnx").is_file()
    assert (result / "mask_decoder.onnx").is_file()
    metadata = json.loads((result / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["format"] == "onnx"
    assert metadata["model_kind"] == "sam2"
    assert metadata["precision"] == precision
    assert metadata["image_size"] == 1024
    assert metadata["batch"] == 1
    assert metadata["encoder_inputs"]["image"] == "[1, 3, 1024, 1024]"
    assert metadata["validation"] == {"enabled": False, "samples": 0}
    assert not quantize_calls


def test_sam2_int8_export_is_rejected(monkeypatch, tmp_path):
    from src.services.model_export import sam_onnx

    source = tmp_path / "sam2.1_hiera_base_plus.pt"
    source.write_bytes(b"checkpoint")
    monkeypatch.setattr(
        sam_onnx,
        "_load_sam2_model",
        lambda *_args: (_ for _ in ()).throw(AssertionError("must reject before loading")),
    )

    with pytest.raises(ValueError, match="暂不支持 INT8"):
        sam_onnx.export_sam2_model_to_directory(
            {
                "model": str(source),
                "precision": "int8",
                "output_dir": str(tmp_path / "exports"),
            }
        )


def test_sam2_export_failure_preserves_existing_artifact(monkeypatch, tmp_path):
    from src.services.model_export import sam_onnx

    source = tmp_path / "sam2.1_hiera_base_plus.pt"
    source.write_bytes(b"checkpoint")
    output = tmp_path / "exports"
    target = output / "sam2.1_hiera_base_plus_sam2_onnx_fp32"
    target.mkdir(parents=True)
    (target / "metadata.json").write_text("old", encoding="utf-8")

    monkeypatch.setattr(
        sam_onnx,
        "_load_sam2_model",
        lambda _path: (_ for _ in ()).throw(RuntimeError("load failed")),
    )

    with pytest.raises(RuntimeError, match="load failed"):
        sam_onnx.export_sam2_model_to_directory(
            {
                "model": str(source),
                "precision": "fp32",
                "simplify": False,
                "output_dir": str(output),
            }
        )

    assert (target / "metadata.json").read_text(encoding="utf-8") == "old"
    assert not list(output.glob(".sam2-export-*"))


def test_sam2_fp32_metadata_disables_quantized_validation(monkeypatch, tmp_path):
    import torch

    from src.services.model_export import sam_onnx

    source = tmp_path / "sam2.1_hiera_base_plus.pt"
    source.write_bytes(b"checkpoint")
    calibration_dir = tmp_path / "calibration"
    calibration_dir.mkdir()
    from PIL import Image

    Image.new("RGB", (8, 8), color="white").save(calibration_dir / "one.png")

    class FakeModel:
        def parameters(self):
            yield torch.zeros(1)

    class FakeEncoderWrapper:
        def __init__(self, _model):
            self.module = self

        def eval(self):
            return self

        def __call__(self, _image):
            return (
                torch.zeros(1, 1, 1, 1),
                torch.zeros(1, 1, 1, 1),
                torch.zeros(1, 1, 1, 1),
            )

    class FakeDecoderWrapper:
        def __init__(self, _model):
            self.module = self

        def eval(self):
            return self

    def fake_export(_module, _args, target, input_names, output_names, **_kwargs):
        _write_fixture(Path(target), input_names, output_names)

    monkeypatch.setattr(
        sam_onnx,
        "_load_sam2_model",
        lambda _path: (FakeModel(), SimpleNamespace(config_name="sam2/config.yaml")),
    )
    monkeypatch.setattr(sam_onnx, "_Sam2ImageEncoderWrapper", FakeEncoderWrapper)
    monkeypatch.setattr(sam_onnx, "_Sam2MaskDecoderWrapper", FakeDecoderWrapper)
    monkeypatch.setattr(sam_onnx, "_export_onnx", fake_export)
    result = sam_onnx.export_sam2_model_to_directory(
        {
            "model": str(source),
            "precision": "fp32",
            "simplify": False,
            "output_dir": str(tmp_path / "exports"),
            "calibration_data": str(calibration_dir),
            "calibration_samples": 1,
        }
    )

    metadata = json.loads((result / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["validation"] == {"enabled": False, "samples": 0}
