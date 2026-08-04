from __future__ import annotations

import json
from pathlib import Path

from src.services.model_export.calibration_sources import CalibrationSet


def write_metadata(
    target: Path,
    model_path: Path,
    config_name: str,
    *,
    precision: str,
    simplify: bool,
    calibration: CalibrationSet | None,
    validation: dict[str, object] | None,
) -> None:
    metadata = {
        "format": "onnx",
        "model_kind": "sam2",
        "precision": precision,
        "source_model": model_path.name,
        "config_name": config_name,
        "image_size": 1024,
        "batch": 1,
        "simplify": bool(simplify),
        "calibration": {"source": str(calibration.source) if calibration else "", "samples": calibration.count if calibration else 0},
        "validation": validation or {"enabled": False, "samples": 0},
        "prompt": {"point_coords": [1, 1, 2], "point_labels": [1, 1], "label_values": {"positive": 1, "negative": 0, "padding": -1}},
        "artifacts": {"image_encoder": "image_encoder.onnx", "mask_decoder": "mask_decoder.onnx"},
        "encoder_inputs": {"image": "[1, 3, 1024, 1024]"},
        "encoder_outputs": {"image_embed": "[1, 256, 64, 64]", "high_res_0": "[1, 32, 256, 256]", "high_res_1": "[1, 64, 128, 128]"},
        "decoder_inputs": {"image_embed": "[1, 256, 64, 64]", "high_res_0": "[1, 32, 256, 256]", "high_res_1": "[1, 64, 128, 128]", "point_coords": "[1, 1, 2]", "point_labels": "[1, 1]"},
        "decoder_outputs": {"high_res_masks": "[1, 3, 1024, 1024]", "iou_predictions": "[1, 3]", "low_res_masks": "[1, 3, 256, 256]"},
    }
    target.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


__all__ = ["write_metadata"]
