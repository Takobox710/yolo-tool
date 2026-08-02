from __future__ import annotations

from pathlib import Path

from src.services.model_export.calibration import CalibrationSet, resolve_calibration_images
from src.services.model_export.capabilities import capabilities_for, dynamic_axes, model_kind_from_path
from src.services.model_export.formats import resolve_export_format


def backend_options(config) -> dict:
    """Build only the Ultralytics arguments supported by the selected backend."""

    capabilities = capabilities_for(
        config.export_format,
        model_kind_from_path(config.model_path),
    )
    options = {
        "format": config.export_format,
        "imgsz": int(config.imgsz),
    }
    if config.export_format == "torchscript" and config.precision == "fp16":
        options["device"] = "0"
    if capabilities.supports_batch:
        options["batch"] = int(config.batch)
    if config.export_format != "onnx" and any(dynamic_axes(config)):
        options["dynamic"] = True
    if capabilities.supports_simplify:
        options["simplify"] = bool(config.simplify)
    if capabilities.supports_nms:
        options.update(
            {
                "nms": bool(config.nms),
                # The public settings keep the nms_ prefix to avoid collisions
                # with inference settings; Ultralytics uses these backend names.
                "conf": float(config.nms_conf),
                "iou": float(config.nms_iou),
                "max_det": int(config.nms_max_det),
                "agnostic_nms": bool(config.agnostic_nms),
            }
        )
    if capabilities.supports_opset and config.opset is not None:
        options["opset"] = int(config.opset)
    if capabilities.supports_workspace and config.workspace is not None:
        options["workspace"] = float(config.workspace)
    if capabilities.supports_optimize:
        options["optimize"] = bool(config.optimize)
    return options


def resolve_calibration(config) -> CalibrationSet | None:
    if config.precision != "int8":
        return None
    return resolve_calibration_images(config.calibration_data, config.calibration_samples)


def backend_calibration_data(calibration: CalibrationSet, work: Path) -> Path:
    import yaml

    work.mkdir(parents=True, exist_ok=True)
    image_list = work / "calibration-images.txt"
    image_list.write_text(
        "\n".join(str(path) for path in calibration.images) + "\n",
        encoding="utf-8",
    )
    dataset = work / "calibration-dataset.yaml"
    dataset.write_text(
        yaml.safe_dump(
            {
                "path": str(work),
                "train": image_list.name,
                "val": image_list.name,
                "names": {0: "calibration"},
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return dataset


def export_yolo_backend(
    model: object,
    source_copy: Path,
    work: Path,
    config,
    calibration: CalibrationSet | None,
) -> Path:
    options = backend_options(config)
    options["quantize"] = {"fp32": 32, "fp16": 16, "int8": 8}[config.precision]
    if calibration is not None and config.export_format in {"openvino", "engine"}:
        options["data"] = str(backend_calibration_data(calibration, work))
    generated_value = model.export(**options)
    generated = resolve_generated_path(generated_value, source_copy, work, config.export_format)
    if not generated.exists():
        raise RuntimeError("转换进程未生成预期的模型文件。")
    return generated


def resolve_generated_path(
    generated_value: object,
    source_copy: Path,
    work: Path,
    export_format: str,
) -> Path:
    generated = Path(str(generated_value))
    if not generated.is_absolute():
        generated = work / generated
    if generated.exists():
        return generated
    suffix = resolve_export_format(export_format).artifact_suffix
    expected = (
        source_copy.parent / f"{source_copy.stem}{suffix}"
        if suffix.startswith("_")
        else source_copy.with_suffix(suffix)
    )
    for candidate in (expected, work / expected.name):
        if candidate.exists():
            return candidate
    matches = sorted(work.glob(f"{source_copy.stem}*{suffix}"))
    return matches[0] if matches else generated


def precision_file_name(source_copy: Path, export_format: str, precision: str) -> str:
    suffix = resolve_export_format(export_format).artifact_suffix
    return f"{source_copy.stem}_{precision}{suffix}"


__all__ = [
    "backend_calibration_data",
    "backend_options",
    "export_yolo_backend",
    "precision_file_name",
    "resolve_calibration",
    "resolve_generated_path",
]
