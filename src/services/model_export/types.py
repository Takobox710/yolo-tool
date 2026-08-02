from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ExportFormatSpec:
    display_name: str
    argument: str
    built_in: bool
    artifact_suffix: str
    required_modules: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ModelExportConfig:
    model_path: Path
    output_dir: Path
    export_format: str = "onnx"
    imgsz: int = 640
    simplify: bool = True
    precision: str = "fp32"
    batch: int = 1
    dynamic_batch: bool = False
    dynamic_height: bool = False
    dynamic_width: bool = False
    nms: bool = False
    nms_conf: float = 0.25
    nms_iou: float = 0.45
    nms_max_det: int = 300
    agnostic_nms: bool = False
    opset: int | None = None
    workspace: float | None = None
    optimize: bool = False
    calibration_data: str = ""
    calibration_samples: int = 300
    validate_quantized: bool = True
    validation_samples: int = 16


@dataclass(frozen=True, slots=True)
class ExportCapabilities:
    """Configuration surface supported by one export target and model kind."""

    export_format: str
    model_kind: str = "yolo"
    precisions: tuple[str, ...] = ("fp32",)
    supports_batch: bool = True
    supports_dynamic_batch: bool = False
    supports_dynamic_height: bool = False
    supports_dynamic_width: bool = False
    supports_simplify: bool = False
    supports_nms: bool = False
    supports_opset: bool = False
    supports_workspace: bool = False
    supports_optimize: bool = False
    supports_calibration: bool = False
    supports_quantized_validation: bool = False
    requires_gpu: bool = False
    fixed_imgsz: int | None = None
    fixed_batch: int | None = None
    reason: str = ""


@dataclass(frozen=True, slots=True)
class ExportCapability:
    available: bool
    runtime: str
    reason: str
    executable: Path | None = None


@dataclass(frozen=True, slots=True)
class InstalledExtension:
    version: str
    root: Path
    package_dir: Path
    supported_formats: tuple[str, ...]
    manifest: dict
