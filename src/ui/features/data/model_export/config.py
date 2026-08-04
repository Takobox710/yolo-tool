from __future__ import annotations

import os
from pathlib import Path

from src.services.model_export import (
    ModelExportConfig,
    model_kind_from_path,
    normalize_model_export_config,
    resolve_export_format,
    validate_model_export_config,
    validate_model_export_source,
)


def collect_config(page) -> ModelExportConfig:
    model_text = page.model_combo.currentText().strip()
    model_path = Path(model_path_from_text(page, model_text))
    if not model_path.is_file() or model_path.suffix.lower() != ".pt":
        raise ValueError("请选择存在的 .pt 模型文件。")
    spec = resolve_export_format(page.format_combo.currentText())
    model_kind = model_kind_from_path(model_path)
    if model_kind == "sam2":
        imgsz = 1024
    else:
        try:
            imgsz = int(page.imgsz_edit.text())
        except ValueError as exc:
            raise ValueError("输入尺寸必须是整数。") from exc
        if imgsz < 32 or imgsz % 32:
            raise ValueError("输入尺寸必须是不小于 32 的 32 倍数。")
    validate_model_export_source(model_path, spec.argument)
    output_root = Path(page.resolve_path_text(page.output_edit))
    precision = {"FP16": "fp16", "INT8": "int8"}.get(
        page.precision_combo.currentText(), "fp32"
    )
    calibration_data = page.resolve_path_text(page.calibration_data_edit)
    if spec.argument == "onnx":
        dynamic_batch = page.onnx_dynamic_batch_check.isChecked()
        dynamic_height = page.onnx_dynamic_size_check.isChecked()
        dynamic_width = page.onnx_dynamic_size_check.isChecked()
    else:
        dynamic_input = page.dynamic_input_check.isChecked()
        dynamic_batch = (
            dynamic_input
            if page._uses_unified_dynamic_input(spec.argument, model_kind)
            else page.dynamic_batch_check.isChecked()
        )
        dynamic_height = (
            dynamic_input
            if page._uses_unified_dynamic_input(spec.argument, model_kind)
            else page.dynamic_height_check.isChecked()
        )
        dynamic_width = (
            dynamic_input
            if page._uses_unified_dynamic_input(spec.argument, model_kind)
            else page.dynamic_width_check.isChecked()
        )
    config = ModelExportConfig(
        model_path=model_path,
        output_dir=output_root / model_path.stem,
        export_format=spec.argument,
        imgsz=imgsz,
        simplify=page.simplify_check.isChecked(),
        precision=precision,
        batch=1 if model_kind == "sam2" else page.batch_spin.value(),
        dynamic_batch=dynamic_batch,
        dynamic_height=dynamic_height,
        dynamic_width=dynamic_width,
        nms=page.nms_check.isChecked(),
        nms_conf=page.conf_spin.value(),
        nms_iou=page.iou_spin.value(),
        nms_max_det=page.max_det_spin.value(),
        agnostic_nms=page.agnostic_nms_check.isChecked(),
        opset=page.opset_spin.value() or None,
        workspace=page.workspace_spin.value(),
        optimize=page.optimize_check.isChecked(),
        calibration_data=calibration_data,
        calibration_samples=page.calibration_samples_spin.value(),
        validate_quantized=page.validate_quantized_check.isChecked(),
        validation_samples=page.validation_samples_spin.value(),
    )
    config = normalize_model_export_config(config, model_kind=model_kind)
    return validate_model_export_config(config, model_kind=model_kind)


def model_path_from_text(page, value: str) -> str:
    path = page._model_display_paths.get(str(value).strip())
    if path is not None:
        return str(path)
    return resolve_project_value(page, value)


def resolve_project_value(page, value: str) -> str:
    path = Path(os.path.expandvars(value)).expanduser()
    return str(path if path.is_absolute() else (page.project_root() / path).resolve())
