from __future__ import annotations

import json
import contextlib
import io
import shutil
import uuid
from pathlib import Path
from typing import Callable

from src.services.annotation.sam_assist import sam_model_spec_from_path


SAM2_ONNX_FORMAT = "sam2_onnx"
SAM2_IMAGE_SIZE = 1024
SAM2_OPSET = 18


def sam2_export_source_error(model_path: str | Path) -> str | None:
    spec = sam_model_spec_from_path(Path(model_path))
    if spec is None:
        return "SAM2 ONNX 导出只接受可识别的 SAM 2 或 SAM 2.1 checkpoint。"
    if spec.runtime_kind != "sam2":
        return f"模型“{Path(model_path).name}”不是 SAM 2/2.1 checkpoint。"
    return None


def _remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def cleanup_stale_sam2_export_workdirs(output_dir: str | Path) -> None:
    root = Path(output_dir)
    if not root.exists():
        return
    backup_prefix = ".sam2-export-backup-"
    for path in root.glob(".sam2-export-*"):
        if not path.name.startswith(backup_prefix):
            _remove_path(path)
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


def _load_sam2_model(model_path: Path, config_name: str | None = None):
    error = sam2_export_source_error(model_path)
    if error:
        raise ValueError(error)
    import torch
    from sam2.build_sam import build_sam2

    spec = sam_model_spec_from_path(model_path)
    assert spec is not None
    model = build_sam2(
        config_name or spec.config_name,
        ckpt_path=str(model_path.resolve()),
        device="cuda" if torch.cuda.is_available() else "cpu",
        apply_postprocessing=False,
    )
    model.eval()
    return model, spec


class _Sam2ImageEncoderWrapper:
    def __init__(self, model):
        import torch.nn as nn

        class Wrapper(nn.Module):
            def __init__(self, sam_model):
                super().__init__()
                self.model = sam_model

            def forward(self, image):
                backbone_out = self.model.forward_image(image)
                _, vision_feats, _, _ = self.model._prepare_backbone_features(backbone_out)
                if self.model.directly_add_no_mem_embed:
                    vision_feats[-1] = vision_feats[-1] + self.model.no_mem_embed
                feat_sizes = ((256, 256), (128, 128), (64, 64))
                feats = [
                    feat.permute(1, 2, 0).reshape(1, -1, *feat_size)
                    for feat, feat_size in zip(vision_feats[::-1], feat_sizes[::-1])
                ][::-1]
                return feats[-1], feats[0], feats[1]

        self.module = Wrapper(model)


class _Sam2MaskDecoderWrapper:
    def __init__(self, model):
        import torch.nn as nn

        class Wrapper(nn.Module):
            def __init__(self, sam_model):
                super().__init__()
                self.model = sam_model

            def forward(
                self,
                image_embed,
                high_res_0,
                high_res_1,
                point_coords,
                point_labels,
            ):
                sparse_embeddings, dense_embeddings = self.model.sam_prompt_encoder(
                    points=(point_coords, point_labels),
                    boxes=None,
                    masks=None,
                )
                low_res_masks, iou_predictions, _tokens, _object_scores = (
                    self.model.sam_mask_decoder(
                        image_embeddings=image_embed,
                        image_pe=self.model.sam_prompt_encoder.get_dense_pe(),
                        sparse_prompt_embeddings=sparse_embeddings,
                        dense_prompt_embeddings=dense_embeddings,
                        multimask_output=True,
                        repeat_image=False,
                        high_res_features=[high_res_0, high_res_1],
                    )
                )
                import torch.nn.functional as functional

                high_res_masks = functional.interpolate(
                    low_res_masks.float(),
                    size=(SAM2_IMAGE_SIZE, SAM2_IMAGE_SIZE),
                    mode="bilinear",
                    align_corners=False,
                )
                return high_res_masks, iou_predictions.float(), low_res_masks.float()

        self.module = Wrapper(model)


def _export_onnx(module, args, target: Path, input_names: list[str], output_names: list[str]) -> None:
    import torch

    module.eval()
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        torch.onnx.export(
            module,
            args,
            str(target),
            input_names=input_names,
            output_names=output_names,
            opset_version=SAM2_OPSET,
            dynamo=True,
            external_data=False,
        )


def _write_metadata(target: Path, model_path: Path, config_name: str) -> None:
    metadata = {
        "format": SAM2_ONNX_FORMAT,
        "source_model": model_path.name,
        "config_name": config_name,
        "image_size": SAM2_IMAGE_SIZE,
        "batch": 1,
        "prompt": {
            "point_coords": [1, 1, 2],
            "point_labels": [1, 1],
            "label_values": {"positive": 1, "negative": 0, "padding": -1},
        },
        "artifacts": {
            "image_encoder": "image_encoder.onnx",
            "mask_decoder": "mask_decoder.onnx",
        },
        "decoder_outputs": {
            "high_res_masks": "[1, 3, 1024, 1024]",
            "iou_predictions": "[1, 3]",
            "low_res_masks": "[1, 3, 256, 256]",
        },
    }
    target.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _validate_onnx_files(target: Path) -> None:
    import onnx

    for name in ("image_encoder.onnx", "mask_decoder.onnx"):
        model = onnx.load(str(target / name), load_external_data=False)
        onnx.checker.check_model(model)


def export_sam2_model_to_directory(
    options: dict,
    *,
    progress: Callable[[str], None] | None = None,
) -> Path:
    values = dict(options)
    model_path = Path(str(values.get("model", ""))).resolve()
    output_dir_value = str(values.get("output_dir", "")).strip()
    if not model_path.is_file() or model_path.suffix.lower() != ".pt":
        raise ValueError("请选择存在的 .pt SAM2 模型文件。")
    error = sam2_export_source_error(model_path)
    if error:
        raise ValueError(error)
    output_dir = (
        Path(output_dir_value).resolve()
        if output_dir_value
        else model_path.parent
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    cleanup_stale_sam2_export_workdirs(output_dir)
    target = output_dir / f"{model_path.stem}_{SAM2_ONNX_FORMAT}"
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
        image = torch.zeros(
            1, 3, SAM2_IMAGE_SIZE, SAM2_IMAGE_SIZE, device=device
        )
        point_coords = torch.zeros(1, 1, 2, device=device)
        point_labels = torch.ones(1, 1, dtype=torch.int32, device=device)
        encoder = _Sam2ImageEncoderWrapper(model).module
        decoder = _Sam2MaskDecoderWrapper(model).module
        if progress:
            progress("正在导出 SAM2 图像编码器：image_encoder.onnx")
        _export_onnx(
            encoder,
            (image,),
            stage / "image_encoder.onnx",
            ["image"],
            ["image_embed", "high_res_0", "high_res_1"],
        )
        with torch.inference_mode():
            image_embed, high_res_0, high_res_1 = encoder(image)
        if progress:
            progress("正在导出 SAM2 点提示解码器：mask_decoder.onnx")
        _export_onnx(
            decoder,
            (image_embed, high_res_0, high_res_1, point_coords, point_labels),
            stage / "mask_decoder.onnx",
            ["image_embed", "high_res_0", "high_res_1", "point_coords", "point_labels"],
            ["high_res_masks", "iou_predictions", "low_res_masks"],
        )
        _write_metadata(stage / "metadata.json", model_path, spec.config_name)
        _validate_onnx_files(stage)
        if target.exists():
            target.replace(backup)
        shutil.move(str(stage), str(target))
        _remove_path(backup)
        if progress:
            progress(f"SAM2 ONNX 导出结果已保存：{target}")
        return target
    except Exception:
        if backup.exists():
            _remove_path(target)
            backup.replace(target)
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)
        if backup.exists() and target.exists():
            _remove_path(backup)


__all__ = [
    "SAM2_IMAGE_SIZE",
    "SAM2_ONNX_FORMAT",
    "cleanup_stale_sam2_export_workdirs",
    "export_sam2_model_to_directory",
    "sam2_export_source_error",
]
