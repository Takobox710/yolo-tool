"""Compatibility façade for calibration source, image and ONNX helpers."""

from src.services.model_export.calibration_images import (
    IMAGE_SUFFIXES,
    SAM2_IMAGE_MEAN,
    SAM2_IMAGE_STD,
    load_image_tensor,
    load_sam2_image_tensor,
)
from src.services.model_export.calibration_sources import (
    CalibrationSet,
    resolve_calibration_images,
)
from src.services.model_export.onnx_quantization import (
    OnnxCalibrationDataReader,
    convert_onnx_to_fp16,
    quantize_onnx_static,
    quantize_onnx_static_with_reader,
)
from src.services.model_export.onnx_validation import (
    smoke_validate_onnx,
    write_validation_metadata,
)

__all__ = [
    "CalibrationSet",
    "OnnxCalibrationDataReader",
    "convert_onnx_to_fp16",
    "load_image_tensor",
    "load_sam2_image_tensor",
    "quantize_onnx_static",
    "quantize_onnx_static_with_reader",
    "resolve_calibration_images",
    "smoke_validate_onnx",
    "write_validation_metadata",
]
