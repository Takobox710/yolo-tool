from __future__ import annotations

from pathlib import Path

import pytest


def _config(tmp_path: Path, **overrides):
    from src.services.model_export import ModelExportConfig

    values = {
        "model_path": tmp_path / "model.pt",
        "output_dir": tmp_path / "output",
        "export_format": "onnx",
    }
    values.update(overrides)
    return ModelExportConfig(**values)

def test_calibration_sources_are_detected_and_limited(tmp_path):
    from src.services.model_export.calibration import resolve_calibration_images
    from src.services.model_export.execute import _backend_calibration_data

    from PIL import Image

    image_dir = tmp_path / "images"
    image_dir.mkdir()
    for index in range(4):
        Image.new("RGB", (8, 8), color=(index, index, index)).save(
            image_dir / f"image-{index}.png"
        )
    limited = resolve_calibration_images(image_dir, 2)
    assert limited.count == 2

    backend_dataset = _backend_calibration_data(limited, tmp_path / "backend")
    backend_text = backend_dataset.read_text(encoding="utf-8")
    assert "train: calibration-images.txt" in backend_text
    assert "calibration-images.txt" in backend_text
    image_list = backend_dataset.parent / "calibration-images.txt"
    assert image_list.read_text(encoding="utf-8").splitlines() == [
        str(path) for path in limited.images
    ]

    dataset_dir = tmp_path / "dataset" / "val"
    dataset_dir.mkdir(parents=True)
    Image.new("RGB", (8, 8), color="white").save(dataset_dir / "val.png")
    dataset = tmp_path / "dataset.yaml"
    dataset.write_text(
        "path: dataset\nval: val\n",
        encoding="utf-8",
    )
    resolved = resolve_calibration_images(dataset, 300)
    assert resolved.images == ((dataset_dir / "val.png").resolve(),)

def test_generated_calibration_dataset_loads_in_ultralytics(tmp_path):
    from PIL import Image

    from src.services.model_export.backend import backend_calibration_data
    from src.services.model_export.calibration import CalibrationSet

    from ultralytics.cfg import DEFAULT_CFG, get_cfg
    from ultralytics.data import build_yolo_dataset
    from ultralytics.data.utils import check_det_dataset

    image = tmp_path / "image.png"
    Image.new("RGB", (32, 32), color="white").save(image)
    (tmp_path / "image.txt").write_text("", encoding="utf-8")
    calibration = CalibrationSet(tmp_path, (image,))

    dataset_yaml = backend_calibration_data(calibration, tmp_path / "backend")
    data = check_det_dataset(str(dataset_yaml), autodownload=False)
    cfg = get_cfg(
        DEFAULT_CFG,
        {
            "task": "detect",
            "imgsz": 32,
            "fraction": 1.0,
            "rect": False,
            "cache": False,
            "single_cls": False,
            "classes": None,
        },
    )
    dataset = build_yolo_dataset(
        cfg,
        data["val"],
        1,
        data,
        mode="val",
        fraction=1.0,
    )

    assert len(dataset) == 1
    assert Path(dataset.im_files[0]).resolve() == image.resolve()

def test_onnx_fp16_int8_and_smoke_validation_with_fixture(tmp_path):
    import numpy as np
    import onnx
    from onnx import TensorProto, helper, numpy_helper
    from PIL import Image

    from src.services.model_export.calibration import (
        convert_onnx_to_fp16,
        quantize_onnx_static,
        resolve_calibration_images,
        smoke_validate_onnx,
    )
    from src.services.model_export.onnx_utils import check_onnx

    input_value = helper.make_tensor_value_info("images", TensorProto.FLOAT, [1, 3, 8, 8])
    output_value = helper.make_tensor_value_info("output", TensorProto.FLOAT, [1, 3, 8, 8])
    weight = numpy_helper.from_array(np.ones((3, 3, 1, 1), dtype=np.float32), "weight")
    bias = numpy_helper.from_array(np.zeros((3,), dtype=np.float32), "bias")
    graph = helper.make_graph(
        [
            helper.make_node("Conv", ["images", "weight", "bias"], ["conv"]),
            helper.make_node("Relu", ["conv"], ["output"]),
        ],
        "export-fixture",
        [input_value],
        [output_value],
        [weight, bias],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
    model.ir_version = 10
    source = tmp_path / "fixture.onnx"
    onnx.save(model, source)
    check_onnx(source)

    image_dir = tmp_path / "calibration"
    image_dir.mkdir()
    for index in range(2):
        Image.new("RGB", (8, 8), color=(index * 20, 10, 5)).save(
            image_dir / f"image-{index}.png"
        )
    calibration = resolve_calibration_images(image_dir, 300)

    fp16 = tmp_path / "fixture_fp16.onnx"
    convert_onnx_to_fp16(source, fp16)
    check_onnx(fp16)

    int8 = tmp_path / "fixture_int8.onnx"
    quantize_onnx_static(source, int8, calibration)
    check_onnx(int8)
    result = smoke_validate_onnx(int8, calibration.images, 16)
    assert result["samples"] == 2
    assert result["inputs"] == ["images"]
    assert result["outputs"]

def test_onnx_export_enables_dynamic_graph_only_when_requested(tmp_path):
    import onnx
    from onnx import TensorProto, helper

    from src.services.model_export.execute import _export_yolo_onnx
    from src.services.model_export import ModelExportConfig

    captured = {}
    generated_dir = tmp_path / "generated"
    generated_dir.mkdir()
    input_value = helper.make_tensor_value_info("images", TensorProto.FLOAT, [1, 3, 8, 8])
    output_value = helper.make_tensor_value_info("output0", TensorProto.FLOAT, [1, 3, 8, 8])
    graph = helper.make_graph(
        [helper.make_node("Identity", ["images"], ["output0"])],
        "dynamic-export-fixture",
        [input_value],
        [output_value],
    )
    fixture = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
    fixture.ir_version = 10

    class FakeModel:
        def export(self, **options):
            captured.update(options)
            path = generated_dir / "model.onnx"
            onnx.save(fixture, path)
            return str(path)

    source = tmp_path / "model.pt"
    source.write_bytes(b"weights")
    work = tmp_path / "work"
    work.mkdir()
    config = ModelExportConfig(
        model_path=source,
        output_dir=tmp_path / "output",
        export_format="onnx",
        simplify=False,
        dynamic_height=True,
    )

    _export_yolo_onnx(FakeModel(), source, work, config, None, None)

    assert captured["dynamic"] is True
