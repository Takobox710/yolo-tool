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


def test_capability_matrix_matches_backend_boundaries():
    from src.services.model_export import capabilities_for

    onnx = capabilities_for("onnx")
    sam2 = capabilities_for("onnx", "sam2")
    torchscript = capabilities_for("torchscript")
    openvino = capabilities_for("openvino")
    tensorrt = capabilities_for("engine")
    ncnn = capabilities_for("ncnn")

    assert onnx.precisions == ("fp32", "fp16", "int8")
    assert onnx.supports_opset and onnx.supports_quantized_validation
    assert sam2.precisions == ("fp32", "fp16")
    assert sam2.fixed_imgsz == 1024 and sam2.fixed_batch == 1
    assert sam2.supports_batch is False
    assert sam2.supports_opset is False
    assert not sam2.supports_calibration
    assert not sam2.supports_quantized_validation
    assert torchscript.precisions == ("fp32", "fp16")
    assert torchscript.supports_optimize and not torchscript.supports_calibration
    assert openvino.supports_calibration and not openvino.supports_simplify
    assert tensorrt.requires_gpu and tensorrt.supports_workspace
    assert not tensorrt.supports_opset
    assert ncnn.precisions == ("fp32", "fp16")
    assert not ncnn.supports_dynamic_width and not ncnn.supports_nms
    assert not ncnn.supports_simplify


def test_legacy_format_and_quantize_values_are_normalized(tmp_path):
    from src.services.model_export import (
        config_from_options,
        normalize_model_export_config,
    )

    config = config_from_options(
        {
            "format": "sam2_onnx",
            "quantize": "16",
            "simplify": "true",
        },
        model_path=tmp_path / "sam2.1_hiera_base_plus.pt",
        output_dir=tmp_path / "output",
    )
    normalized = normalize_model_export_config(config, model_kind="sam2")

    assert normalized.export_format == "onnx"
    assert normalized.precision == "fp16"
    assert normalized.imgsz == 1024
    assert normalized.batch == 1
    assert normalized.dynamic_batch is False
    assert normalized.nms is False
    assert normalized.opset is None


def test_invalid_options_are_rejected_instead_of_dropped(tmp_path):
    from src.services.model_export import validate_model_export_config

    with pytest.raises(ValueError, match="opset"):
        validate_model_export_config(
            _config(tmp_path, export_format="engine", opset=17)
        )
    with pytest.raises(ValueError, match="图简化"):
        validate_model_export_config(
            _config(tmp_path, export_format="ncnn", simplify=True)
        )
    with pytest.raises(ValueError, match="动态轴"):
        validate_model_export_config(
            _config(tmp_path, export_format="ncnn", simplify=False, dynamic_width=True)
        )
    with pytest.raises(ValueError, match="INT8"):
        validate_model_export_config(
            _config(tmp_path, export_format="ncnn", simplify=False, precision="int8")
        )
    openvino_config = validate_model_export_config(
        _config(
            tmp_path,
            export_format="openvino",
            simplify=False,
            precision="int8",
            calibration_data=str(tmp_path),
            validate_quantized=True,
        ),
        strict=False,
    )
    assert openvino_config.validate_quantized is False
    with pytest.raises(ValueError, match="batch 大于 1"):
        validate_model_export_config(
            _config(
                tmp_path,
                export_format="engine",
                simplify=False,
                dynamic_height=True,
            )
        )
    with pytest.raises(ValueError, match="不能与 FP16"):
        validate_model_export_config(
            _config(
                tmp_path,
                export_format="torchscript",
                simplify=False,
                precision="fp16",
                optimize=True,
            )
        )


def test_nms_options_are_validated_and_only_supported_formats_receive_them(tmp_path):
    from src.services.model_export import ModelExportConfig, build_model_export_command

    config = _config(
        tmp_path,
        nms=True,
        nms_conf=0.4,
        nms_iou=0.6,
        nms_max_det=128,
        agnostic_nms=True,
    )
    command = build_model_export_command(config)
    assert "nms=true" in command
    assert "nms_conf=0.4" in command
    assert "nms_iou=0.6" in command
    assert "nms_max_det=128" in command
    assert "agnostic_nms=true" in command

    ncnn_command = build_model_export_command(
        ModelExportConfig(
            model_path=tmp_path / "model.pt",
            output_dir=tmp_path / "output",
            export_format="ncnn",
            simplify=False,
        )
    )
    assert not any(item.startswith("nms=") for item in ncnn_command)


def test_export_command_omits_options_outside_each_format_capability(tmp_path):
    from src.services.model_export import ModelExportConfig, build_model_export_command

    common = {
        "model_path": tmp_path / "model.pt",
        "output_dir": tmp_path / "output",
        "imgsz": 640,
        "batch": 2,
        "dynamic_batch": True,
        "dynamic_height": True,
        "dynamic_width": True,
        "nms": True,
        "nms_conf": 0.4,
        "nms_iou": 0.6,
        "nms_max_det": 128,
        "agnostic_nms": True,
    }

    torchscript = build_model_export_command(
        ModelExportConfig(
            export_format="torchscript", simplify=False, optimize=True, **common
        ),
    )
    assert "format=torchscript" in torchscript
    assert "dynamic_batch=true" in torchscript
    assert "nms=true" in torchscript
    assert "optimize=true" in torchscript
    assert not any(item.startswith("simplify=") for item in torchscript)
    assert not any(item.startswith("opset=") for item in torchscript)
    assert not any(item.startswith("workspace=") for item in torchscript)

    openvino = build_model_export_command(
        ModelExportConfig(
            export_format="openvino",
            precision="int8",
            simplify=False,
            calibration_data=str(tmp_path),
            **common,
        )
    )
    assert "format=openvino" in openvino
    assert "nms=true" in openvino
    assert "calibration_data=" + str(tmp_path) in openvino
    assert not any(item.startswith("simplify=") for item in openvino)
    assert not any(item.startswith("opset=") for item in openvino)
    assert not any(item.startswith("workspace=") for item in openvino)
    assert not any(item.startswith("optimize=") for item in openvino)

    ncnn = build_model_export_command(
        ModelExportConfig(
            export_format="ncnn",
            simplify=False,
            **{
                key: value
                for key, value in common.items()
                if key
                not in {
                    "nms",
                    "nms_conf",
                    "nms_iou",
                    "nms_max_det",
                    "agnostic_nms",
                    "dynamic_batch",
                    "dynamic_height",
                    "dynamic_width",
                }
            },
        )
    )
    assert "format=ncnn" in ncnn
    assert not any(
        item.startswith(prefix)
        for item in ncnn
        for prefix in (
            "dynamic_batch=",
            "dynamic_height=",
            "dynamic_width=",
            "nms=",
            "opset=",
            "workspace=",
            "optimize=",
            "simplify=",
        )
    )


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


def test_torchscript_fp16_requires_gpu(monkeypatch):
    from src.services.model_export import runtime

    monkeypatch.setattr(runtime, "cuda_available", lambda: False)
    monkeypatch.setattr(runtime, "_modules_available", lambda _modules: True)

    capability = runtime.export_capability(
        "torchscript", precision="fp16", frozen=False
    )
    assert capability.available is False
    assert "GPU" in capability.reason


def test_backend_options_keep_fp16_torchscript_on_gpu(tmp_path):
    from src.services.model_export import ModelExportConfig
    from src.services.model_export.backend import backend_options

    options = backend_options(
        ModelExportConfig(
            model_path=tmp_path / "model.pt",
            output_dir=tmp_path / "output",
            export_format="torchscript",
            precision="fp16",
            dynamic_batch=True,
        )
    )

    assert options["device"] == "0"
    assert options["dynamic"] is True


def test_backend_options_map_public_nms_fields_to_ultralytics_names(tmp_path):
    from src.services.model_export import ModelExportConfig
    from src.services.model_export.backend import backend_options

    options = backend_options(
        ModelExportConfig(
            model_path=tmp_path / "model.pt",
            output_dir=tmp_path / "output",
            nms=True,
            nms_conf=0.4,
            nms_iou=0.6,
            nms_max_det=128,
            agnostic_nms=True,
        )
    )

    assert options["nms"] is True
    assert options["conf"] == 0.4
    assert options["iou"] == 0.6
    assert options["max_det"] == 128
    assert options["agnostic_nms"] is True
    assert "nms_conf" not in options
    assert "nms_iou" not in options
    assert "nms_max_det" not in options


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
