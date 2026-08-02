from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Callable

from src.services.model_export.calibration import (
    CalibrationSet,
    convert_onnx_to_fp16,
    quantize_onnx_static,
    resolve_calibration_images,
    smoke_validate_onnx,
)
from src.services.model_export.capabilities import (
    capabilities_for,
    dynamic_axes,
    model_kind_from_path,
    validate_model_export_config,
)
from src.services.model_export.backend import (
    backend_calibration_data as _backend_calibration_data,
    backend_options as _backend_options,
    export_yolo_backend as _export_yolo_backend,
    precision_file_name as _precision_file_name,
    resolve_calibration as _resolve_calibration,
    resolve_generated_path as _resolve_generated_path,
)
from src.services.model_export.formats import (
    export_artifact_path,
    resolve_export_format,
    validate_model_export_source,
)
from src.services.model_export.onnx_utils import (
    check_onnx,
    constrain_onnx_dynamic_axes,
    simplify_onnx_graph,
    update_onnx_metadata,
)
from src.services.model_export.options import config_from_options


def _remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def cleanup_stale_export_workdirs(output_dir: str | Path) -> None:
    root = Path(output_dir)
    if not root.exists():
        return
    for path in root.glob(".yolo-export-*"):
        if not path.name.startswith(".yolo-export-backup-"):
            _remove_path(path)
    backup_prefix = ".yolo-export-backup-"
    for backup in root.glob(f"{backup_prefix}*"):
        remainder = backup.name[len(backup_prefix) :]
        _token, separator, target_name = remainder.partition("-")
        if not separator or not target_name:
            _remove_path(backup)
            continue
        target = root / target_name
        if target.exists():
            _remove_path(backup)
        else:
            backup.replace(target)


def export_model_to_directory(
    options: dict,
    *,
    yolo_factory: Callable[[str], object] | None,
    progress: Callable[[str], None] | None = None,
) -> Path:
    values = dict(options)
    model_path = Path(str(values.pop("model", ""))).resolve()
    output_dir_value = str(values.pop("output_dir", "")).strip()
    if not model_path.is_file() or model_path.suffix.lower() != ".pt":
        raise ValueError("请选择存在的 .pt 模型文件。")
    output_dir = (
        Path(output_dir_value).resolve() if output_dir_value else model_path.parent
    )
    config = config_from_options(values, model_path=model_path, output_dir=output_dir)
    config = validate_model_export_config(config)
    validate_model_export_source(model_path, config.export_format)
    if model_kind_from_path(model_path) == "sam2":
        from src.services.model_export.sam_onnx import export_sam2_model_to_directory

        sam_options = dict(values)
        sam_options.update(
            {
                "model": str(model_path),
                "output_dir": str(output_dir),
                "format": "onnx",
                "precision": config.precision,
                "simplify": config.simplify,
                "calibration_data": config.calibration_data,
                "calibration_samples": config.calibration_samples,
                "validate_quantized": config.validate_quantized,
                "validation_samples": config.validation_samples,
            }
        )
        return export_sam2_model_to_directory(sam_options, progress=progress)
    if yolo_factory is None:
        raise ValueError("YOLO 导出缺少 Ultralytics 运行时。")

    output_dir.mkdir(parents=True, exist_ok=True)
    cleanup_stale_export_workdirs(output_dir)
    target = export_artifact_path(
        model_path,
        output_dir,
        config.export_format,
        config.precision,
    )
    work = output_dir / f".yolo-export-{uuid.uuid4().hex}"
    backup = output_dir / f".yolo-export-backup-{uuid.uuid4().hex}-{target.name}"
    work.mkdir()
    source_copy = work / model_path.name
    calibration: CalibrationSet | None = None
    replaced = False
    try:
        shutil.copy2(model_path, source_copy)
        calibration = _resolve_calibration(config)
        if progress:
            progress(f"正在加载模型：{model_path.name}")
        model = yolo_factory(str(source_copy))
        if config.export_format == "onnx":
            generated = _export_yolo_onnx(
                model,
                source_copy,
                work,
                config,
                calibration,
                progress,
            )
        else:
            generated = _export_yolo_backend(
                model, source_copy, work, config, calibration
            )
        if not generated.exists():
            raise RuntimeError("转换进程未生成预期的模型文件。")
        if target.exists():
            target.replace(backup)
            replaced = True
        shutil.move(str(generated), str(target))
        _remove_path(backup)
        if progress:
            progress(f"转换结果已保存：{target}")
        return target
    except Exception:
        if replaced and backup.exists():
            _remove_path(target)
            backup.replace(target)
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)
        if backup.exists() and target.exists():
            _remove_path(backup)


def _export_yolo_onnx(
    model: object,
    source_copy: Path,
    work: Path,
    config,
    calibration: CalibrationSet | None,
    progress: Callable[[str], None] | None,
) -> Path:
    backend = _backend_options(config)
    backend.update(
        {
            "format": "onnx",
            "quantize": 32,
            "half": False,
            "int8": False,
            # Ultralytics builds the shape-aware graph when dynamic=True.
            # The selected axes are narrowed after export so each checkbox
            # remains independent at the model interface.
            "dynamic": any(dynamic_axes(config)),
            "simplify": False,
        }
    )
    generated_value = model.export(**backend)
    generated = _resolve_generated_path(generated_value, source_copy, work, "onnx")
    if not generated.exists():
        raise RuntimeError("转换进程未生成预期的 ONNX 文件。")
    if not _is_valid_onnx(generated):
        # Keep the small fake exporters used by callers and legacy integrations working.
        if config.precision != "fp32" or any(dynamic_axes(config)):
            raise RuntimeError("导出的 ONNX 文件无法读取，不能继续进行精度或动态轴处理。")
        return generated
    if config.simplify:
        if progress:
            progress("正在简化 ONNX 图结构")
        simplify_onnx_graph(generated)
    batch_dynamic, height_dynamic, width_dynamic = dynamic_axes(config)
    if batch_dynamic or height_dynamic or width_dynamic:
        constrain_onnx_dynamic_axes(
            generated,
            dynamic_batch=batch_dynamic,
            dynamic_height=height_dynamic,
            dynamic_width=width_dynamic,
            batch=config.batch,
            imgsz=config.imgsz,
        )
    check_onnx(generated)
    if config.precision == "fp32":
        update_onnx_metadata(
            generated,
            _onnx_export_metadata(config, calibration=None),
        )
        return generated
    target = work / _precision_file_name(source_copy, "onnx", config.precision)
    if config.precision == "fp16":
        if progress:
            progress("正在转换 ONNX FP16 权重")
        converted = convert_onnx_to_fp16(generated, target)
        update_onnx_metadata(converted, _onnx_export_metadata(config, calibration=None))
        return converted
    if calibration is None:
        raise ValueError("INT8 导出缺少校准数据。")
    if progress:
        progress(f"正在执行 ONNX INT8 静态量化，校准样本：{calibration.count}")
    quantized = quantize_onnx_static(
        generated,
        target,
        calibration,
        default_imgsz=config.imgsz,
    )
    check_onnx(quantized)
    validation = None
    if config.validate_quantized:
        result = smoke_validate_onnx(
            quantized,
            calibration.images,
            config.validation_samples,
            default_imgsz=config.imgsz,
        )
        if progress:
            progress(f"量化后 ONNX 冒烟验证通过，样本：{result['samples']}")
        validation = result
    update_onnx_metadata(
        quantized,
        _onnx_export_metadata(config, calibration=calibration, validation=validation),
    )
    return quantized


def _onnx_export_metadata(
    config,
    *,
    calibration: CalibrationSet | None,
    validation: dict | None = None,
) -> dict[str, object]:
    return {
        "yolotool.export_format": "onnx",
        "yolotool.precision": config.precision,
        "yolotool.simplify": config.simplify,
        "yolotool.dynamic_axes": {
            "batch": config.dynamic_batch,
            "height": config.dynamic_height,
            "width": config.dynamic_width,
        },
        "yolotool.calibration_source": str(calibration.source) if calibration else "",
        "yolotool.calibration_samples": calibration.count if calibration else 0,
        "yolotool.validation": validation or {
            "enabled": False,
            "samples": 0,
        },
    }


def _is_valid_onnx(path: Path) -> bool:
    try:
        check_onnx(path)
    except Exception:
        return False
    return True


__all__ = ["cleanup_stale_export_workdirs", "export_model_to_directory"]
