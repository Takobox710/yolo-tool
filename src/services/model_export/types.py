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
