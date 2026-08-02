from __future__ import annotations

from pathlib import Path
from typing import Any


class Sam2OnnxCanvasRuntime:
    image_size = 1024

    def __init__(self) -> None:
        self.encoder = None
        self.decoder = None
        self.features = None
        self.original_hw: tuple[int, int] | None = None

    def load_model(self, model_dir: Path) -> None:
        import onnxruntime as ort

        encoder_path = model_dir / "image_encoder.onnx"
        decoder_path = model_dir / "mask_decoder.onnx"
        if not encoder_path.is_file() or not decoder_path.is_file():
            raise FileNotFoundError(
                "SAM2 ONNX 模型目录必须同时包含 image_encoder.onnx 和 mask_decoder.onnx。"
            )
        providers = ["CPUExecutionProvider"]
        self.encoder = ort.InferenceSession(str(encoder_path), providers=providers)
        self.decoder = ort.InferenceSession(str(decoder_path), providers=providers)
        if not self.encoder.get_inputs() or not self.decoder.get_inputs():
            raise ValueError("SAM2 ONNX 模型输入不完整。")

    def set_image(self, image_path: Path) -> None:
        if self.encoder is None:
            raise RuntimeError("SAM2 ONNX 模型尚未加载。")
        import numpy as np
        from PIL import Image

        with Image.open(image_path) as image:
            rgb = image.convert("RGB")
            width, height = rgb.size
            resized = rgb.resize(
                (self.image_size, self.image_size),
                Image.Resampling.BILINEAR,
            )
            array = np.asarray(resized, dtype=np.float32).transpose(2, 0, 1)[None]
        array = array / 255.0
        mean = np.asarray([0.485, 0.456, 0.406], dtype=np.float32).reshape(1, 3, 1, 1)
        std = np.asarray([0.229, 0.224, 0.225], dtype=np.float32).reshape(1, 3, 1, 1)
        image_tensor = (array - mean) / std
        input_name = self.encoder.get_inputs()[0].name
        self.features = self.encoder.run(None, {input_name: image_tensor})
        if len(self.features) < 3:
            raise ValueError("SAM2 ONNX 编码器输出不完整。")
        self.original_hw = (height, width)

    def predict_point(
        self,
        x: float,
        y: float,
        *,
        multimask_output: bool,
    ) -> tuple[Any, Any]:
        del multimask_output
        if self.decoder is None or self.features is None or self.original_hw is None:
            raise RuntimeError("SAM2 ONNX 当前图片特征尚未就绪。")
        import numpy as np

        height, width = self.original_hw
        point_coords = np.asarray(
            [[[
                float(x) * self.image_size / max(1, width),
                float(y) * self.image_size / max(1, height),
            ]]],
            dtype=np.float32,
        )
        feed = {
            "image_embed": self.features[0],
            "high_res_0": self.features[1],
            "high_res_1": self.features[2],
            "point_coords": point_coords,
            "point_labels": np.ones((1, 1), dtype=np.int32),
        }
        input_names = {item.name for item in self.decoder.get_inputs()}
        outputs = self.decoder.run(None, {name: feed[name] for name in input_names})
        if len(outputs) < 2:
            raise ValueError("SAM2 ONNX 解码器输出不完整。")
        masks = np.asarray(outputs[0])[0]
        scores = np.asarray(outputs[1])[0]
        if masks.ndim != 3 or scores.ndim != 1:
            raise ValueError("SAM2 ONNX 解码器输出形状无效。")
        if masks.shape[1:] != (self.image_size, self.image_size):
            raise ValueError("SAM2 ONNX 掩膜输出必须是 1024x1024。")
        if (height, width) != (self.image_size, self.image_size):
            import cv2

            masks = np.asarray(
                [
                    cv2.resize(mask, (width, height), interpolation=cv2.INTER_LINEAR)
                    for mask in masks
                ]
            )
        return masks > 0.0, scores

    def close(self) -> None:
        self.features = None
        self.encoder = None
        self.decoder = None
        self.original_hw = None


__all__ = ["Sam2OnnxCanvasRuntime"]
