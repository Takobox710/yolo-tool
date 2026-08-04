from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Callable

from src.services.annotation.sam_assist import sam_model_spec_from_path
from src.services.model_export.calibration import CalibrationSet, convert_onnx_to_fp16
from src.services.model_export.onnx_utils import check_onnx, simplify_onnx_graph
from src.services.model_export.sam_onnx_components import (
    SAM2_IMAGE_SIZE,
    SAM2_OPSET,
    Sam2ImageEncoderWrapper as _Sam2ImageEncoderWrapper,
    Sam2MaskDecoderWrapper as _Sam2MaskDecoderWrapper,
    export_onnx as _export_onnx,
    load_sam2_model as _load_sam2_model,
)
from src.services.model_export.sam_onnx_metadata import write_metadata as _write_metadata
from src.services.model_export.sam_onnx_transaction import (
    cleanup_stale_sam2_export_workdirs,
    promote_stage,
    remove_path as _remove_path,
    rollback_target,
)


SAM2_ONNX_FORMAT = "sam2_onnx"


def sam2_export_source_error(model_path: str | Path) -> str | None:
    spec = sam_model_spec_from_path(Path(model_path))
    if spec is None:
        return "ONNX 导出只接受可识别的 SAM 2 或 SAM 2.1 checkpoint。"
    if spec.runtime_kind != "sam2":
        return f"模型“{Path(model_path).name}”不是 SAM 2/2.1 checkpoint。"
    return None


def export_sam2_model_to_directory(options: dict, *, progress: Callable[[str], None] | None = None) -> Path:
    values = dict(options)
    model_path = Path(str(values.get("model", ""))).resolve()
    output_dir = Path(str(values.get("output_dir", "") or model_path.parent)).resolve()
    precision = _normalize_precision(values.get("precision", values.get("quantize", "32")))
    if precision == "int8":
        raise ValueError("SAM2/SAM2.1 ONNX 暂不支持 INT8：当前静态量化会破坏点提示分割质量。请使用 FP16 或 FP32。")
    simplify = _as_bool(values.get("simplify", True), True)
    calibration: CalibrationSet | None = None
    if not model_path.is_file() or model_path.suffix.lower() != ".pt":
        raise ValueError("请选择存在的 .pt SAM2 模型文件。")
    error = sam2_export_source_error(model_path)
    if error:
        raise ValueError(error)
    output_dir.mkdir(parents=True, exist_ok=True)
    cleanup_stale_sam2_export_workdirs(output_dir)
    target = output_dir / f"{model_path.stem}_sam2_onnx_{precision}"
    work = output_dir / f".sam2-export-{uuid.uuid4().hex}"
    backup = output_dir / f".sam2-export-backup-{uuid.uuid4().hex}-{target.name}"
    stage = work / target.name
    stage.mkdir(parents=True)
    try:
        if progress:
            progress(f"正在加载 SAM2 模型：{model_path.name}")
        model, spec = _load_sam2_model(model_path)
        import torch

        device = next(model.parameters()).device
        image = torch.zeros(1, 3, SAM2_IMAGE_SIZE, SAM2_IMAGE_SIZE, device=device)
        point_coords = torch.zeros(1, 1, 2, device=device)
        point_labels = torch.ones(1, 1, dtype=torch.int32, device=device)
        encoder = _Sam2ImageEncoderWrapper(model).module
        decoder = _Sam2MaskDecoderWrapper(model).module
        encoder_path = stage / "image_encoder.onnx"
        decoder_path = stage / "mask_decoder.onnx"
        if progress:
            progress("正在导出 SAM2 图像编码器：image_encoder.onnx")
        _export_onnx(encoder, (image,), encoder_path, ["image"], ["image_embed", "high_res_0", "high_res_1"])
        with torch.inference_mode():
            image_embed, high_res_0, high_res_1 = encoder(image)
        if progress:
            progress("正在导出 SAM2 点提示解码器：mask_decoder.onnx")
        _export_onnx(
            decoder,
            (image_embed, high_res_0, high_res_1, point_coords, point_labels),
            decoder_path,
            ["image_embed", "high_res_0", "high_res_1", "point_coords", "point_labels"],
            ["high_res_masks", "iou_predictions", "low_res_masks"],
        )
        for path in (encoder_path, decoder_path):
            check_onnx(path)
            if simplify:
                simplify_onnx_graph(path)
            check_onnx(path)
        if precision == "fp16":
            if progress:
                progress("正在转换 SAM2 ONNX FP16 权重")
            _convert_sam2_precision(stage, precision="fp16")
        _validate_onnx_files(stage)
        _write_metadata(stage / "metadata.json", model_path, spec.config_name, precision=precision, simplify=simplify, calibration=calibration, validation=None)
        promote_stage(stage, target, backup)
        _remove_path(backup)
        if progress:
            progress(f"SAM2 ONNX 导出结果已保存：{target}")
        return target
    except Exception:
        rollback_target(target, backup)
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)
        if backup.exists() and target.exists():
            _remove_path(backup)


def _convert_sam2_precision(stage: Path, *, precision: str) -> None:
    for name in ("image_encoder.onnx", "mask_decoder.onnx"):
        source = stage / name
        converted = stage / f".{name}.converted"
        convert_onnx_to_fp16(source, converted)
        converted.replace(source)


def _validate_onnx_files(target: Path) -> None:
    for name in ("image_encoder.onnx", "mask_decoder.onnx"):
        check_onnx(target / name)


def _normalize_precision(value: object) -> str:
    normalized = str(value or "32").strip().lower()
    try:
        return {"32": "fp32", "fp32": "fp32", "16": "fp16", "fp16": "fp16", "8": "int8", "int8": "int8"}[normalized]
    except KeyError as exc:
        raise ValueError("导出精度必须是 fp32、fp16 或 int8。") from exc


def _as_bool(value: object, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value or "").strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return fallback


__all__ = ["SAM2_IMAGE_SIZE", "SAM2_ONNX_FORMAT", "cleanup_stale_sam2_export_workdirs", "export_sam2_model_to_directory", "sam2_export_source_error"]
