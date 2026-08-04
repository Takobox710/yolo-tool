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
