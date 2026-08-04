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
