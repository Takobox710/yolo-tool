from __future__ import annotations

from pathlib import Path

from src.services.model_export.types import ExportFormatSpec
from src.services.data_ops import simplified_model_path
from src.services.validation.model_catalog import find_result_model_paths


EXPORT_FORMATS: tuple[ExportFormatSpec, ...] = (
    ExportFormatSpec(
        "ONNX", "onnx", True, ".onnx", ("onnx", "onnxslim", "onnxruntime")
    ),
    ExportFormatSpec("TorchScript", "torchscript", True, ".torchscript", ("torch",)),
    ExportFormatSpec("OpenVINO", "openvino", False, "_openvino_model", ("openvino",)),
    ExportFormatSpec("TensorRT", "engine", False, ".engine", ("tensorrt",)),
    ExportFormatSpec("NCNN", "ncnn", False, "_ncnn_model", ("ncnn", "pnnx")),
)


def resolve_export_format(value: str) -> ExportFormatSpec:
    normalized = str(value or "").strip().lower()
    for spec in EXPORT_FORMATS:
        if normalized in {spec.argument.lower(), spec.display_name.lower()}:
            return spec
    supported = ", ".join(spec.display_name for spec in EXPORT_FORMATS)
    raise ValueError(f"不支持的模型格式：{value}。可用格式：{supported}")


def export_display_names() -> list[str]:
    return [spec.display_name for spec in EXPORT_FORMATS]


def export_artifact_name(model_path: str | Path, export_format: str) -> str:
    source = Path(model_path)
    spec = resolve_export_format(export_format)
    return f"{source.stem}{spec.artifact_suffix}"


def export_artifact_path(
    model_path: str | Path, output_dir: str | Path, export_format: str
) -> Path:
    return Path(output_dir) / export_artifact_name(model_path, export_format)


def find_export_model_paths(
    project_root: Path,
    app_root: Path | None = None,
    *,
    show_last_training_models: bool = False,
) -> list[Path]:
    del app_root
    project_root = Path(project_root)
    candidates = find_result_model_paths(
        project_root / "result",
        show_last_training_models=show_last_training_models,
    )
    result: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        resolved = Path(path).resolve()
        key = str(resolved).lower()
        if key not in seen and resolved.is_file() and resolved.suffix.lower() == ".pt":
            seen.add(key)
            result.append(resolved)
    return result


def export_model_display_path(path: str | Path, project_root: Path) -> str:
    return simplified_model_path(str(path), project_root)
