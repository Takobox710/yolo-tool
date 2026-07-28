from __future__ import annotations

import gc
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from src.shared.paths import ROOT
from src.services.annotation.sam_assist import sam_geometry_from_mask


SAM3_CHECKPOINT_NAME = "sam3.pt"
SAM3_OUTPUT_SHAPES = {"rect", "obb", "polygon"}


@dataclass(frozen=True, slots=True)
class Sam3Candidate:
    class_id: int
    score: float
    mask: np.ndarray
    points: list[tuple[float, float]]
    order: int


@dataclass(frozen=True, slots=True)
class Sam3InferenceStats:
    raw_count: int
    area_filtered: int
    overlap_filtered: int


def is_sam3_checkpoint(path: str | Path) -> bool:
    return Path(path).name.lower() == SAM3_CHECKPOINT_NAME


def find_sam3_model_paths(project_root: Path, app_root: Path | None = None) -> list[Path]:
    roots = [Path(project_root).resolve()]
    resolved_app_root = Path(ROOT if app_root is None else app_root).resolve()
    if resolved_app_root not in roots:
        roots.append(resolved_app_root)
    results: list[Path] = []
    seen_names: set[str] = set()
    for root in roots:
        path = root / "data" / "models" / SAM3_CHECKPOINT_NAME
        key = path.name.lower()
        if path.is_file() and key not in seen_names:
            results.append(path.resolve())
            seen_names.add(key)
    return results


def normalize_sam3_prompts(
    class_names: list[str],
    prompts: dict[str, str],
    enabled_classes: list[str],
) -> list[tuple[int, str, str]]:
    enabled = set(str(value).strip() for value in enabled_classes if str(value).strip())
    normalized: list[tuple[int, str, str]] = []
    for class_id, class_name in enumerate(class_names):
        name = str(class_name).strip()
        if not name or (enabled and name not in enabled):
            continue
        prompt = str(prompts.get(name, name)).strip()
        if prompt:
            normalized.append((class_id, name, prompt))
    return normalized


def mask_iou(left: np.ndarray, right: np.ndarray) -> float:
    left_bool = np.asarray(left, dtype=bool)
    right_bool = np.asarray(right, dtype=bool)
    intersection = int(np.count_nonzero(left_bool & right_bool))
    union = int(np.count_nonzero(left_bool | right_bool))
    return float(intersection / union) if union else 0.0


def _deduplicate_candidates(
    candidates: list[Sam3Candidate],
    overlap_iou: float,
) -> tuple[list[Sam3Candidate], int]:
    ordered = sorted(candidates, key=lambda item: (-item.score, item.order))
    accepted: list[Sam3Candidate] = []
    filtered = 0
    threshold = max(0.0, min(1.0, float(overlap_iou)))
    for candidate in ordered:
        if any(mask_iou(candidate.mask, other.mask) > threshold for other in accepted):
            filtered += 1
            continue
        accepted.append(candidate)
    return accepted, filtered


def sam3_annotations_from_masks(
    masks: list[Any],
    scores: list[Any],
    class_id: int,
    output_shape: str,
    minimum_area: float,
    simplification_ratio: float,
    order_start: int,
) -> tuple[list[Sam3Candidate], int]:
    shape = str(output_shape).strip()
    if shape not in SAM3_OUTPUT_SHAPES:
        raise ValueError(f"不支持的 SAM 3 标注形状：{shape}")
    candidates: list[Sam3Candidate] = []
    area_filtered = 0
    for index, (mask, score) in enumerate(zip(masks, scores)):
        array = np.asarray(mask).squeeze()
        if array.ndim != 2:
            area_filtered += 1
            continue
        geometry = sam_geometry_from_mask(
            array,
            float(score),
            minimum_area=float(minimum_area),
            simplification_ratio=float(simplification_ratio),
        )
        if geometry is None:
            area_filtered += 1
            continue
        if shape == "rect":
            points = geometry.rectangle
        elif shape == "obb":
            points = geometry.oriented_rectangle
        else:
            points = geometry.polygon
        candidates.append(
            Sam3Candidate(
                class_id=int(class_id),
                score=float(score),
                mask=array > 0.5,
                points=list(points),
                order=order_start + index,
            )
        )
    return candidates, area_filtered


class Sam3TextRuntime:
    def __init__(self) -> None:
        self.model = None
        self.processor = None
        self.state: dict[str, Any] | None = None
        self.checkpoint_path = ""

    def load_model(self, checkpoint_path: str) -> None:
        import torch

        if not torch.cuda.is_available():
            raise RuntimeError("SAM 3 文本预标注需要 CUDA GPU，当前环境未检测到 CUDA。")
        checkpoint = Path(checkpoint_path)
        if not checkpoint.is_file():
            raise FileNotFoundError(f"SAM 3 模型文件不存在：{checkpoint}")
        if not is_sam3_checkpoint(checkpoint):
            raise ValueError("SAM 3 文本预标注只支持官方 sam3.pt 权重。")
        self.release_model()
        from sam3.model.sam3_image_processor import Sam3Processor
        from sam3.model_builder import build_sam3_image_model

        self.model = build_sam3_image_model(
            checkpoint_path=str(checkpoint.resolve()),
            load_from_HF=False,
            device="cuda",
            compile=False,
        )
        self.processor = Sam3Processor(self.model, device="cuda")
        self.checkpoint_path = str(checkpoint.resolve())

    def set_image(self, image_path: Path) -> None:
        if self.processor is None:
            raise RuntimeError("SAM 3 文本预标注模型尚未加载。")
        with Image.open(image_path) as image:
            self.state = self.processor.set_image(image.convert("RGB"))

    def predict_prompt(self, prompt: str, confidence: float) -> tuple[list[Any], list[Any]]:
        if self.processor is None or self.state is None:
            raise RuntimeError("SAM 3 当前图片特征尚未就绪。")
        self.processor.set_confidence_threshold(float(confidence))
        output = self.processor.set_text_prompt(prompt, self.state)
        masks = output.get("masks")
        scores = output.get("scores")
        if masks is None or scores is None:
            return [], []
        return _to_cpu_list(masks), _to_cpu_list(scores)

    def release_model(self) -> None:
        self.state = None
        self.processor = None
        self.model = None
        self.checkpoint_path = ""
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

    def close(self) -> None:
        self.release_model()


def _to_cpu_list(value: Any) -> list[Any]:
    if hasattr(value, "detach"):
        value = value.detach().cpu().numpy()
    return list(np.asarray(value))


__all__ = [
    "SAM3_CHECKPOINT_NAME",
    "SAM3_OUTPUT_SHAPES",
    "Sam3Candidate",
    "Sam3InferenceStats",
    "Sam3TextRuntime",
    "find_sam3_model_paths",
    "is_sam3_checkpoint",
    "mask_iou",
    "normalize_sam3_prompts",
    "sam3_annotations_from_masks",
]
