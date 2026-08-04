from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from src.services.model_export.calibration_images import load_image_tensor
from src.services.model_export.calibration_sources import CalibrationSet
from src.services.model_export.onnx_utils import topologically_sort_onnx_graph


class OnnxCalibrationDataReader:
    """ONNX Runtime static-quantization reader for NCHW image inputs."""

    def __init__(self, model_path: str | Path, images: Iterable[str | Path], *, default_imgsz: int = 640) -> None:
        import onnx

        model = onnx.load(str(model_path), load_external_data=False)
        if not model.graph.input:
            raise ValueError("ONNX 模型没有输入，无法建立校准 reader。")
        input_value = model.graph.input[0]
        tensor_shape = input_value.type.tensor_type.shape.dim
        self.input_name = input_value.name
        self.batch = _dimension(tensor_shape, 0, 1)
        self.height = _dimension(tensor_shape, 2, default_imgsz)
        self.width = _dimension(tensor_shape, 3, default_imgsz)
        self.images = tuple(Path(path) for path in images)
        self._index = 0

    def get_next(self) -> dict[str, Any] | None:
        if self._index >= len(self.images):
            return None
        image = self.images[self._index]
        self._index += 1
        return {self.input_name: load_image_tensor(image, height=self.height, width=self.width, batch=self.batch)}


def convert_onnx_to_fp16(source: str | Path, target: str | Path) -> Path:
    from onnxruntime.transformers.float16 import convert_float_to_float16
    import onnx

    source = Path(source)
    target = Path(target)
    model = onnx.load(str(source), load_external_data=False)
    converted = convert_float_to_float16(model, keep_io_types=True)
    topologically_sort_onnx_graph(converted)
    onnx.save(converted, str(target))
    return target


def quantize_onnx_static(source: str | Path, target: str | Path, calibration: CalibrationSet, *, default_imgsz: int = 640) -> Path:
    reader = OnnxCalibrationDataReader(source, calibration.images, default_imgsz=default_imgsz)
    return quantize_onnx_static_with_reader(source, target, reader)


def quantize_onnx_static_with_reader(source: str | Path, target: str | Path, reader: Any) -> Path:
    from onnxruntime.quantization import QuantFormat, QuantType, quantize_static

    source = Path(source)
    target = Path(target)
    try:
        quantize_static(str(source), str(target), reader, quant_format=QuantFormat.QDQ, activation_type=QuantType.QInt8, weight_type=QuantType.QInt8, per_channel=True)
    except TypeError:
        quantize_static(str(source), str(target), reader, quant_format=QuantFormat.QDQ, activation_type=QuantType.QInt8, weight_type=QuantType.QInt8)
    return target


def _dimension(dimensions: Any, index: int, fallback: int) -> int:
    if index >= len(dimensions):
        return fallback
    dim = dimensions[index]
    value = int(getattr(dim, "dim_value", 0) or 0)
    return value if value > 0 else fallback


__all__ = ["OnnxCalibrationDataReader", "convert_onnx_to_fp16", "quantize_onnx_static", "quantize_onnx_static_with_reader"]
