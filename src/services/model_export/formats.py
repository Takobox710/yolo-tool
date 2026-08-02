from __future__ import annotations

from pathlib import Path

from src.services.annotation.sam_assist import sam_model_spec_from_path
from src.services.model_export.types import ExportFormatSpec
from src.services.data_ops import simplified_model_path
from src.shared.paths import ROOT
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

_FORMAT_ALIASES = {
    "sam2_onnx": "onnx",
    "sam2 onnx": "onnx",
    "tensorrt": "engine",
}


def resolve_export_format(value: str) -> ExportFormatSpec:
    normalized = _FORMAT_ALIASES.get(str(value or "").strip().lower(), str(value or "").strip().lower())
    for spec in EXPORT_FORMATS:
        if normalized in {spec.argument.lower(), spec.display_name.lower()}:
            return spec
    supported = ", ".join(spec.display_name for spec in EXPORT_FORMATS)
    raise ValueError(f"不支持的模型格式：{value}。可用格式：{supported}")


def export_display_names() -> list[str]:
    return [spec.display_name for spec in EXPORT_FORMATS]


def export_artifact_name(
    model_path: str | Path,
    export_format: str,
    precision: str = "fp32",
) -> str:
    return export_artifact_name_for_precision(model_path, export_format, precision)


def export_artifact_name_for_precision(
    model_path: str | Path,
    export_format: str,
    precision: str = "fp32",
) -> str:
    source = Path(model_path)
    spec = resolve_export_format(export_format)
    normalized_precision = {
        "32": "fp32",
        "fp32": "fp32",
        "float32": "fp32",
        "16": "fp16",
        "fp16": "fp16",
        "float16": "fp16",
        "8": "int8",
        "int8": "int8",
    }.get(str(precision or "fp32").strip().lower(), "")
    if normalized_precision not in {"fp32", "fp16", "int8"}:
        raise ValueError(f"不支持的导出精度：{precision}")
    sam_spec = sam_model_spec_from_path(source)
    if sam_spec is not None and sam_spec.runtime_kind == "sam2" and spec.argument == "onnx":
        return f"{source.stem}_sam2_onnx_{normalized_precision}"
    return f"{source.stem}_{normalized_precision}{spec.artifact_suffix}"


def export_artifact_path(
    model_path: str | Path,
    output_dir: str | Path,
    export_format: str,
    precision: str = "fp32",
) -> Path:
    return Path(output_dir) / export_artifact_name_for_precision(
        model_path, export_format, precision
    )


def model_export_source_error(
    model_path: str | Path, export_format: str | None = None
) -> str | None:
    path = Path(model_path)
    spec = sam_model_spec_from_path(path)
    if spec is None:
        return None
    requested_format = str(export_format or "onnx").strip().lower()
    if spec.runtime_kind == "sam2":
        if requested_format in {"onnx", "sam2_onnx", "sam2 onnx"}:
            return None
        return (
            f"模型“{path.name}”是 SAM 2/2.1 checkpoint；"
            "SAM2/SAM2.1 目前只支持 ONNX 导出。"
        )
    return (
        f"模型“{path.name}”是 {spec.display_name} checkpoint，不是 Ultralytics YOLO 权重。"
        "当前转换器仅支持 Ultralytics YOLO .pt 模型；"
        "SAM2/SAM2.1 目前只支持 ONNX；SAM1、SAM3 和未知自定义 SAM 名称暂不支持导出。"
    )


def validate_model_export_source(
    model_path: str | Path, export_format: str | None = None
) -> None:
    error = model_export_source_error(model_path, export_format)
    if error:
        raise ValueError(error)


def find_export_model_paths(
    project_root: Path,
    app_root: Path | None = None,
    *,
    show_last_training_models: bool = False,
    include_sam_models: bool = False,
) -> list[Path]:
    project_root = Path(project_root)
    candidates = find_result_model_paths(
        project_root / "result",
        show_last_training_models=show_last_training_models,
    )
    if include_sam_models:
        roots = [project_root / "data" / "models"]
        resolved_app_root = Path(ROOT if app_root is None else app_root)
        if resolved_app_root.resolve() != project_root.resolve():
            roots.append(resolved_app_root / "data" / "models")
        for root in roots:
            if root.is_dir():
                candidates.extend(
                    path
                    for path in root.glob("*.pt")
                    if (
                        sam_model_spec_from_path(path) is not None
                        and sam_model_spec_from_path(path).runtime_kind == "sam2"
                    )
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
