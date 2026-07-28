from __future__ import annotations

import gc
from contextlib import nullcontext
from pathlib import Path
from typing import Any

from src.services.annotation.sam_assist import sam_geometry_from_mask


class SamAssistRuntime:
    def __init__(self) -> None:
        self.model = None
        self.predictor = None
        self.device = ""
        self.model_generation = 0
        self.image_generation = 0
        self.image_path = ""

    def load_model(
        self,
        checkpoint_path: str,
        config_name: str,
        model_generation: int,
    ) -> dict[str, Any]:
        checkpoint = Path(checkpoint_path)
        if not checkpoint.is_file():
            raise FileNotFoundError(f"SAM 模型文件不存在：{checkpoint}")
        if not str(config_name).strip():
            raise ValueError("缺少 SAM 模型配置。")

        self.release_model()
        import torch
        from sam2.build_sam import build_sam2
        from sam2.sam2_image_predictor import SAM2ImagePredictor

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = build_sam2(
            str(config_name),
            ckpt_path=str(checkpoint.resolve()),
            device=self.device,
        )
        self.predictor = SAM2ImagePredictor(self.model)
        self.model_generation = int(model_generation)
        self.image_generation = 0
        self.image_path = ""
        return {
            "state": "model_ready",
            "device": self.device,
            "model_generation": self.model_generation,
        }

    def set_image(
        self,
        image_path: str,
        image_generation: int,
        model_generation: int,
    ) -> dict[str, Any]:
        self._require_model(model_generation)
        from PIL import Image
        import numpy as np
        import torch

        path = Path(image_path)
        if not path.is_file():
            raise FileNotFoundError(f"待标注图片不存在：{path}")
        with Image.open(path) as image:
            image_array = np.asarray(image.convert("RGB")).copy()
        with torch.inference_mode(), self._autocast_context(torch):
            self.predictor.set_image(image_array)
        self.image_generation = int(image_generation)
        self.image_path = str(path.resolve())
        return {
            "state": "image_ready",
            "model_generation": self.model_generation,
            "image_generation": self.image_generation,
            "image_path": self.image_path,
        }

    def predict_point(
        self,
        x: float,
        y: float,
        image_generation: int,
        model_generation: int,
    ) -> dict[str, Any]:
        self._require_model(model_generation)
        if int(image_generation) != self.image_generation or not self.image_path:
            raise RuntimeError("SAM 当前图片特征尚未就绪。")
        import numpy as np
        import torch

        with torch.inference_mode(), self._autocast_context(torch):
            masks, scores, _logits = self.predictor.predict(
                point_coords=np.asarray([[float(x), float(y)]], dtype=np.float32),
                point_labels=np.asarray([1], dtype=np.int32),
                multimask_output=False,
            )
        if len(scores) == 0:
            return {"state": "prediction", "geometry": None}
        geometry = sam_geometry_from_mask(masks[0], float(scores[0]))
        return {
            "state": "prediction",
            "model_generation": self.model_generation,
            "image_generation": self.image_generation,
            "geometry": None if geometry is None else geometry.to_payload(),
        }

    def release_model(self) -> None:
        self.predictor = None
        self.model = None
        self.model_generation = 0
        self.image_generation = 0
        self.image_path = ""
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

    def close(self) -> None:
        self.release_model()

    def _require_model(self, model_generation: int) -> None:
        if self.predictor is None:
            raise RuntimeError("SAM 模型尚未加载。")
        if int(model_generation) != self.model_generation:
            raise RuntimeError("SAM 模型请求已过期。")

    def _autocast_context(self, torch):
        if self.device != "cuda":
            return nullcontext()
        return torch.autocast(device_type="cuda", dtype=torch.bfloat16)


__all__ = ["SamAssistRuntime"]
