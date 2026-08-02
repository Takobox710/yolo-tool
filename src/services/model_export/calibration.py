from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from src.services.model_export.onnx_utils import topologically_sort_onnx_graph


IMAGE_SUFFIXES = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}
SAM2_IMAGE_MEAN = (0.485, 0.456, 0.406)
SAM2_IMAGE_STD = (0.229, 0.224, 0.225)


@dataclass(frozen=True, slots=True)
class CalibrationSet:
    source: Path
    images: tuple[Path, ...]

    @property
    def count(self) -> int:
        return len(self.images)


def resolve_calibration_images(
    value: str | Path,
    sample_limit: int,
) -> CalibrationSet:
    source = Path(str(value or "")).expanduser().resolve()
    sample_limit = int(sample_limit)
    if not source.exists():
        raise ValueError(f"校准数据不存在：{source}")
    if sample_limit < 1:
        raise ValueError("校准样本数必须大于 0。")
    if source.is_dir():
        images = _scan_images(source)
    elif source.suffix.lower() in {".yaml", ".yml"}:
        images = _images_from_dataset_yaml(source)
    elif source.suffix.lower() in IMAGE_SUFFIXES:
        images = [source]
    else:
        images = _images_from_list_file(source)
    images = [path for path in images if path.is_file()]
    if not images:
        raise ValueError(f"校准数据中没有可用图片：{source}")
    return CalibrationSet(source=source, images=tuple(images[:sample_limit]))


def load_image_tensor(
    path: str | Path,
    *,
    height: int,
    width: int,
    batch: int = 1,
):
    import numpy as np
    from PIL import Image

    with Image.open(path) as image:
        image = image.convert("RGB").resize((width, height), Image.Resampling.BILINEAR)
        array = np.asarray(image, dtype=np.float32).transpose(2, 0, 1) / 255.0
    tensor = array[None, ...]
    if batch > 1:
        tensor = np.repeat(tensor, batch, axis=0)
    return tensor


def load_sam2_image_tensor(
    path: str | Path,
    *,
    height: int = 1024,
    width: int = 1024,
    batch: int = 1,
):
    import numpy as np

    tensor = load_image_tensor(
        path,
        height=height,
        width=width,
        batch=batch,
    )
    mean = np.asarray(SAM2_IMAGE_MEAN, dtype=np.float32).reshape(1, 3, 1, 1)
    std = np.asarray(SAM2_IMAGE_STD, dtype=np.float32).reshape(1, 3, 1, 1)
    return (tensor - mean) / std


class OnnxCalibrationDataReader:
    """ONNX Runtime static-quantization reader for NCHW image inputs."""

    def __init__(
        self,
        model_path: str | Path,
        images: Iterable[str | Path],
        *,
        default_imgsz: int = 640,
    ) -> None:
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
        return {
            self.input_name: load_image_tensor(
                image,
                height=self.height,
                width=self.width,
                batch=self.batch,
            )
        }


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


def quantize_onnx_static(
    source: str | Path,
    target: str | Path,
    calibration: CalibrationSet,
    *,
    default_imgsz: int = 640,
) -> Path:
    reader = OnnxCalibrationDataReader(
        source,
        calibration.images,
        default_imgsz=default_imgsz,
    )
    return quantize_onnx_static_with_reader(source, target, reader)


def quantize_onnx_static_with_reader(
    source: str | Path,
    target: str | Path,
    reader: Any,
) -> Path:
    from onnxruntime.quantization import QuantFormat, QuantType, quantize_static

    source = Path(source)
    target = Path(target)
    try:
        quantize_static(
            str(source),
            str(target),
            reader,
            quant_format=QuantFormat.QDQ,
            activation_type=QuantType.QInt8,
            weight_type=QuantType.QInt8,
            per_channel=True,
        )
    except TypeError:
        # Keep compatibility with older ORT wheels in previously frozen instances.
        quantize_static(
            str(source),
            str(target),
            reader,
            quant_format=QuantFormat.QDQ,
            activation_type=QuantType.QInt8,
            weight_type=QuantType.QInt8,
        )
    return target


def smoke_validate_onnx(
    model_path: str | Path,
    images: Iterable[str | Path],
    sample_limit: int,
    *,
    default_imgsz: int = 640,
) -> dict[str, Any]:
    import numpy as np
    import onnxruntime as ort

    sample_limit = int(sample_limit)
    if sample_limit < 1:
        raise ValueError("量化后验证样本数必须大于 0。")
    session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    inputs = session.get_inputs()
    if not inputs:
        raise ValueError("ONNX 模型没有输入。")
    image_paths = tuple(Path(path) for path in images)[:sample_limit]
    if not image_paths:
        raise ValueError("量化后验证没有可用图片。")
    input_info = inputs[0]
    shape = input_info.shape
    if len(shape) < 4:
        raise ValueError("ONNX 模型输入不是 NCHW 图像张量。")
    batch = _runtime_dimension(shape, 0, 1)
    height = _runtime_dimension(shape, 2, default_imgsz)
    width = _runtime_dimension(shape, 3, default_imgsz)
    checked = 0
    output_shapes: list[list[int]] = []
    for path in image_paths:
        feed = {
            input_info.name: load_image_tensor(
                path,
                height=height,
                width=width,
                batch=batch,
            )
        }
        outputs = session.run(None, feed)
        if not outputs:
            raise ValueError(f"ONNX 模型没有输出：{model_path}")
        for output in outputs:
            array = np.asarray(output)
            if array.ndim == 0 or any(int(value) <= 0 for value in array.shape):
                raise ValueError(f"ONNX 输出形状无效：{model_path}")
            if np.issubdtype(array.dtype, np.floating) and not np.isfinite(array).all():
                raise ValueError(f"ONNX 输出包含非有限数值：{model_path}")
            output_shapes.append([int(value) for value in array.shape])
        checked += 1
    return {
        "model": str(Path(model_path).resolve()),
        "samples": checked,
        "inputs": [item.name for item in inputs],
        "outputs": output_shapes,
    }


def write_validation_metadata(path: str | Path, payload: dict[str, Any]) -> None:
    Path(path).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _images_from_dataset_yaml(path: Path) -> list[Path]:
    import yaml

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ValueError(f"无法读取校准 dataset.yaml：{path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"校准 dataset.yaml 格式无效：{path}")
    root_value = payload.get("path") or "."
    root = Path(str(root_value)).expanduser()
    if not root.is_absolute():
        root = (path.parent / root).resolve()
    value = payload.get("val") or payload.get("validation") or payload.get("train")
    return _resolve_yaml_value(value, root)


def _resolve_yaml_value(value: Any, root: Path) -> list[Path]:
    if isinstance(value, (list, tuple)):
        result: list[Path] = []
        for item in value:
            result.extend(_resolve_yaml_value(item, root))
        return result
    if not value:
        return []
    candidate = Path(str(value)).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    if candidate.is_dir():
        return _scan_images(candidate)
    if candidate.is_file() and candidate.suffix.lower() in IMAGE_SUFFIXES:
        return [candidate.resolve()]
    if candidate.is_file():
        return _images_from_list_file(candidate)
    return []


def _images_from_list_file(path: Path) -> list[Path]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"无法读取校准图片列表：{path}") from exc
    result: list[Path] = []
    for line in lines:
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            candidate = path.parent / candidate
        if candidate.is_file() and candidate.suffix.lower() in IMAGE_SUFFIXES:
            result.append(candidate.resolve())
    return result


def _scan_images(root: Path) -> list[Path]:
    return sorted(
        path.resolve()
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )


def _dimension(dimensions: Any, index: int, fallback: int) -> int:
    if index >= len(dimensions):
        return fallback
    dim = dimensions[index]
    value = int(getattr(dim, "dim_value", 0) or 0)
    return value if value > 0 else fallback


def _runtime_dimension(shape: Any, index: int, fallback: int) -> int:
    if index >= len(shape):
        return fallback
    value = shape[index]
    return int(value) if isinstance(value, int) and value > 0 else fallback


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
