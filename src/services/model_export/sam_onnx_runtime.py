from __future__ import annotations

from pathlib import Path

from src.services.model_export.calibration import CalibrationSet, load_sam2_image_tensor


SAM2_IMAGE_SIZE = 1024


def validate_sam2_runtime(
    stage: Path,
    calibration: CalibrationSet | None,
    sample_limit: int,
) -> dict[str, object]:
    if calibration is None:
        raise ValueError("SAM2 量化后验证缺少校准样本。")
    import numpy as np
    import onnxruntime as ort

    sample_limit = int(sample_limit)
    if sample_limit < 1:
        raise ValueError("SAM2 量化后验证样本数必须大于 0。")

    encoder = ort.InferenceSession(
        str(stage / "image_encoder.onnx"),
        providers=["CPUExecutionProvider"],
    )
    decoder = ort.InferenceSession(
        str(stage / "mask_decoder.onnx"),
        providers=["CPUExecutionProvider"],
    )
    encoder_inputs = encoder.get_inputs()
    if not encoder_inputs:
        raise ValueError("SAM2 ONNX 编码器没有输入。")
    encoder_input = encoder_inputs[0].name
    decoder_inputs = decoder.get_inputs()
    decoder_names = [item.name for item in decoder_inputs]
    encoder_outputs = encoder.get_outputs()
    decoder_outputs = decoder.get_outputs()
    required_decoder_names = {
        "image_embed",
        "high_res_0",
        "high_res_1",
        "point_coords",
        "point_labels",
    }
    if not required_decoder_names.issubset(decoder_names):
        raise ValueError("SAM2 ONNX 解码器输入不完整。")
    images = calibration.images[:sample_limit]
    if not images:
        raise ValueError("SAM2 量化后验证没有可用图片。")
    summary: dict[str, object] = {
        "enabled": True,
        "sample_limit": sample_limit,
        "samples": 0,
        "checks": {
            "inputs": True,
            "outputs": True,
            "shapes": True,
            "finite": True,
        },
        "encoder": {
            "inputs": [item.name for item in encoder_inputs],
            "outputs": [item.name for item in encoder_outputs],
        },
        "decoder": {
            "inputs": decoder_names,
            "outputs": [item.name for item in decoder_outputs],
        },
    }
    encoder_shape_summary: list[list[int]] | None = None
    decoder_shape_summary: list[list[int]] | None = None
    encoder_dtype_summary: list[str] | None = None
    decoder_dtype_summary: list[str] | None = None
    for image_path in images:
        image = load_sam2_image_tensor(
            image_path,
            height=SAM2_IMAGE_SIZE,
            width=SAM2_IMAGE_SIZE,
        )
        features = encoder.run(None, {encoder_input: image})
        if len(features) < 3:
            raise ValueError("SAM2 ONNX 编码器输出不完整。")
        current_encoder_shapes: list[list[int]] = []
        current_encoder_dtypes: list[str] = []
        for feature in features:
            array = np.asarray(feature)
            if array.ndim == 0 or any(int(value) < 1 for value in array.shape):
                raise ValueError("SAM2 ONNX 编码器输出形状无效。")
            if np.issubdtype(array.dtype, np.floating) and not np.isfinite(array).all():
                raise ValueError("SAM2 ONNX 编码器输出包含非有限数值。")
            current_encoder_shapes.append([int(value) for value in array.shape])
            current_encoder_dtypes.append(str(array.dtype))
        if encoder_shape_summary is None:
            encoder_shape_summary = current_encoder_shapes
            encoder_dtype_summary = current_encoder_dtypes
        elif current_encoder_shapes != encoder_shape_summary:
            raise ValueError("SAM2 ONNX 编码器输出形状在样本间不一致。")
        feed = {
            "image_embed": features[0],
            "high_res_0": features[1],
            "high_res_1": features[2],
            "point_coords": np.zeros((1, 1, 2), dtype=np.float32),
            "point_labels": np.ones((1, 1), dtype=np.int32),
        }
        if any(name not in feed for name in decoder_names):
            raise ValueError("SAM2 ONNX 解码器输入不完整。")
        outputs = decoder.run(None, {name: feed[name] for name in decoder_names})
        if len(outputs) < 3:
            raise ValueError("SAM2 ONNX 解码器输出不完整。")
        current_decoder_shapes: list[list[int]] = []
        current_decoder_dtypes: list[str] = []
        for output in outputs:
            array = np.asarray(output)
            if array.ndim == 0 or any(int(value) < 1 for value in array.shape):
                raise ValueError("SAM2 ONNX 解码器输出形状无效。")
            if np.issubdtype(array.dtype, np.floating) and not np.isfinite(array).all():
                raise ValueError("SAM2 ONNX 量化后验证输出包含非有限数值。")
            current_decoder_shapes.append([int(value) for value in array.shape])
            current_decoder_dtypes.append(str(array.dtype))
        if decoder_shape_summary is None:
            decoder_shape_summary = current_decoder_shapes
            decoder_dtype_summary = current_decoder_dtypes
        elif current_decoder_shapes != decoder_shape_summary:
            raise ValueError("SAM2 ONNX 解码器输出形状在样本间不一致。")
        summary["samples"] = int(summary["samples"]) + 1

    encoder_summary = summary["encoder"]
    decoder_summary = summary["decoder"]
    assert isinstance(encoder_summary, dict)
    assert isinstance(decoder_summary, dict)
    encoder_summary["output_shapes"] = encoder_shape_summary or []
    encoder_summary["output_dtypes"] = encoder_dtype_summary or []
    decoder_summary["output_shapes"] = decoder_shape_summary or []
    decoder_summary["output_dtypes"] = decoder_dtype_summary or []
    return summary


__all__ = ["validate_sam2_runtime"]
