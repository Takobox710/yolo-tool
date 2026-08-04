from __future__ import annotations

import contextlib
import io
from pathlib import Path

from src.services.annotation.sam_assist import sam_model_spec_from_path

SAM2_IMAGE_SIZE = 1024
SAM2_OPSET = 18


def load_sam2_model(model_path: Path, config_name: str | None = None):
    spec = sam_model_spec_from_path(model_path)
    if spec is None:
        raise ValueError("ONNX 导出只接受可识别的 SAM 2 或 SAM 2.1 checkpoint。")
    if spec.runtime_kind != "sam2":
        raise ValueError(f"模型“{model_path.name}”不是 SAM 2/2.1 checkpoint。")
    import torch
    from sam2.build_sam import build_sam2

    model = build_sam2(
        config_name or spec.config_name,
        ckpt_path=str(model_path.resolve()),
        device="cuda" if torch.cuda.is_available() else "cpu",
        apply_postprocessing=False,
    )
    model.eval()
    return model, spec


class Sam2ImageEncoderWrapper:
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


class Sam2MaskDecoderWrapper:
    def __init__(self, model):
        import torch.nn as nn

        class Wrapper(nn.Module):
            def __init__(self, sam_model):
                super().__init__()
                self.model = sam_model

            def forward(self, image_embed, high_res_0, high_res_1, point_coords, point_labels):
                sparse_embeddings, dense_embeddings = self.model.sam_prompt_encoder(
                    points=(point_coords, point_labels), boxes=None, masks=None
                )
                low_res_masks, iou_predictions, _tokens, _object_scores = self.model.sam_mask_decoder(
                    image_embeddings=image_embed,
                    image_pe=self.model.sam_prompt_encoder.get_dense_pe(),
                    sparse_prompt_embeddings=sparse_embeddings,
                    dense_prompt_embeddings=dense_embeddings,
                    multimask_output=True,
                    repeat_image=False,
                    high_res_features=[high_res_0, high_res_1],
                )
                import torch.nn.functional as functional

                high_res_masks = functional.interpolate(
                    low_res_masks.float(), size=(SAM2_IMAGE_SIZE, SAM2_IMAGE_SIZE), mode="bilinear", align_corners=False
                )
                return high_res_masks, iou_predictions.float(), low_res_masks.float()

        self.module = Wrapper(model)


def export_onnx(module, args, target: Path, input_names: list[str], output_names: list[str], *, opset: int = SAM2_OPSET) -> None:
    import torch

    module.eval()
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        torch.onnx.export(
            module,
            args,
            str(target),
            input_names=input_names,
            output_names=output_names,
            opset_version=opset,
            dynamo=True,
            external_data=False,
        )


__all__ = ["SAM2_IMAGE_SIZE", "SAM2_OPSET", "Sam2ImageEncoderWrapper", "Sam2MaskDecoderWrapper", "export_onnx", "load_sam2_model"]
