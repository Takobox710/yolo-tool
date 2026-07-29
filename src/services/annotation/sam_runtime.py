from __future__ import annotations

import gc
from contextlib import nullcontext
from pathlib import Path
from typing import Any

from src.services.annotation.sam_assist import sam_geometry_from_mask


class _Sam3CanvasRuntime:
    def __init__(self) -> None:
        self.model = None
        self.processor = None
        self.state: dict[str, Any] | None = None

    def load_model(self, checkpoint_path: Path) -> None:
        import torch

        if not torch.cuda.is_available():
            raise RuntimeError("SAM 3 画布辅助标注需要 CUDA GPU，当前环境未检测到 CUDA。")
        from sam3.model.sam3_image_processor import Sam3Processor
        from sam3.model_builder import build_sam3_image_model

        self.model = build_sam3_image_model(
            checkpoint_path=str(checkpoint_path.resolve()),
            load_from_HF=False,
            device="cuda",
            compile=False,
            enable_inst_interactivity=True,
        )
        self.processor = Sam3Processor(self.model, device="cuda")

    def set_image(self, image_path: Path) -> None:
        if self.processor is None:
            raise RuntimeError("SAM 3 模型尚未加载。")
        from PIL import Image
        import torch

        with Image.open(image_path) as image:
            rgb_image = image.convert("RGB")
            autocast_kwargs = {"device_type": "cuda"}
            if hasattr(torch, "bfloat16"):
                autocast_kwargs["dtype"] = torch.bfloat16
            with torch.inference_mode(), torch.autocast(**autocast_kwargs):
                self.state = self.processor.set_image(rgb_image)

    def predict_point(
        self,
        x: float,
        y: float,
        *,
        multimask_output: bool,
    ) -> tuple[Any, Any]:
        if self.model is None or self.state is None:
            raise RuntimeError("SAM 3 当前图片特征尚未就绪。")
        import numpy as np
        import torch

        autocast_kwargs = {"device_type": "cuda"}
        if hasattr(torch, "bfloat16"):
            autocast_kwargs["dtype"] = torch.bfloat16
        with torch.inference_mode(), torch.autocast(**autocast_kwargs):
            masks, scores, _logits = self.model.predict_inst(
                self.state,
                point_coords=np.asarray([[float(x), float(y)]], dtype=np.float32),
                point_labels=np.asarray([1], dtype=np.int32),
                multimask_output=bool(multimask_output),
            )
        return masks, scores

    def close(self) -> None:
        self.state = None
        self.processor = None
        self.model = None


class SamAssistRuntime:
    def __init__(self) -> None:
        self.model = None
        self.predictor = None
        self.sam3_runtime: _Sam3CanvasRuntime | None = None
        self.runtime_kind = ""
        self.device = ""
        self.model_generation = 0
        self.image_generation = 0
        self.image_path = ""

    def load_model(
        self,
        checkpoint_path: str,
        config_name: str,
        model_generation: int,
        runtime_kind: str = "sam2",
    ) -> dict[str, Any]:
        checkpoint = Path(checkpoint_path)
        if not checkpoint.is_file():
            raise FileNotFoundError(f"SAM 模型文件不存在：{checkpoint}")
        backend = str(runtime_kind or "sam2").strip().lower()
        if backend not in {"sam2", "sam3"}:
            raise ValueError("当前 SAM 模型无法从文件名确定可用运行后端。")
        if backend == "sam2" and not str(config_name).strip():
            raise ValueError("缺少 SAM 模型配置。")

        self.release_model()
        import torch

        self.runtime_kind = backend
        if backend == "sam3":
            self.sam3_runtime = _Sam3CanvasRuntime()
            self.sam3_runtime.load_model(checkpoint)
            self.device = "cuda"
        else:
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
        path = Path(image_path)
        if not path.is_file():
            raise FileNotFoundError(f"待标注图片不存在：{path}")
        if self.runtime_kind == "sam3":
            if self.sam3_runtime is None:
                raise RuntimeError("SAM 3 模型尚未加载。")
            self.sam3_runtime.set_image(path)
            self.image_generation = int(image_generation)
            self.image_path = str(path.resolve())
            return {
                "state": "image_ready",
                "model_generation": self.model_generation,
                "image_generation": self.image_generation,
                "image_path": self.image_path,
            }

        from PIL import Image
        import numpy as np
        import torch

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
        multimask_output: bool = False,
        minimum_score: float = 0.0,
        minimum_area: int = 4,
        simplification_ratio: float = 0.002,
    ) -> dict[str, Any]:
        self._require_model(model_generation)
        if int(image_generation) != self.image_generation or not self.image_path:
            raise RuntimeError("SAM 当前图片特征尚未就绪。")
        if self.runtime_kind == "sam3":
            if self.sam3_runtime is None:
                raise RuntimeError("SAM 3 模型尚未加载。")
            masks, scores = self.sam3_runtime.predict_point(
                float(x),
                float(y),
                multimask_output=bool(multimask_output),
            )
        else:
            import numpy as np
            import torch

            with torch.inference_mode(), self._autocast_context(torch):
                masks, scores, _logits = self.predictor.predict(
                    point_coords=np.asarray([[float(x), float(y)]], dtype=np.float32),
                    point_labels=np.asarray([1], dtype=np.int32),
                    multimask_output=bool(multimask_output),
                )
        if len(scores) == 0:
            return {"state": "prediction", "geometry": None}
        import numpy as np

        best_index = int(np.argmax(scores))
        score = float(scores[best_index])
        if score < max(0.0, min(1.0, float(minimum_score))):
            geometry = None
        else:
            geometry = sam_geometry_from_mask(
                masks[best_index],
                score,
                minimum_area=max(1, int(minimum_area)),
                simplification_ratio=max(0.0, min(0.015, float(simplification_ratio))),
            )
        return {
            "state": "prediction",
            "model_generation": self.model_generation,
            "image_generation": self.image_generation,
            "geometry": None if geometry is None else geometry.to_payload(),
        }

    def release_model(self) -> None:
        self.predictor = None
        self.model = None
        if self.sam3_runtime is not None:
            self.sam3_runtime.close()
        self.sam3_runtime = None
        self.runtime_kind = ""
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
        if self.runtime_kind == "sam3" and self.sam3_runtime is None:
            raise RuntimeError("SAM 模型尚未加载。")
        if self.runtime_kind != "sam3" and self.predictor is None:
            raise RuntimeError("SAM 模型尚未加载。")
        if int(model_generation) != self.model_generation:
            raise RuntimeError("SAM 模型请求已过期。")

    def _autocast_context(self, torch):
        if self.device != "cuda":
            return nullcontext()
        return torch.autocast(device_type="cuda", dtype=torch.bfloat16)


__all__ = ["SamAssistRuntime"]
