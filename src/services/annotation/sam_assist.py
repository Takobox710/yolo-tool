from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.shared.paths import ROOT


@dataclass(frozen=True, slots=True)
class SamModelSpec:
    key: str
    display_name: str
    checkpoint_path: Path
    config_name: str
    runtime_kind: str = "unknown"

    @property
    def supports_assist(self) -> bool:
        return self.runtime_kind in {"sam2", "sam3"}


@dataclass(frozen=True, slots=True)
class SamAssistGeometry:
    polygon: list[tuple[float, float]]
    rectangle: list[tuple[float, float]]
    oriented_rectangle: list[tuple[float, float]]
    score: float

    def to_payload(self) -> dict[str, Any]:
        return {
            "polygon": [list(point) for point in self.polygon],
            "rectangle": [list(point) for point in self.rectangle],
            "oriented_rectangle": [list(point) for point in self.oriented_rectangle],
            "score": self.score,
        }


_ARCHITECTURES = (
    ("base_plus", "b+", "Base+"),
    ("base-plus", "b+", "Base+"),
    ("hiera_b+", "b+", "Base+"),
    ("tiny", "t", "Tiny"),
    ("hiera_t", "t", "Tiny"),
    ("small", "s", "Small"),
    ("hiera_s", "s", "Small"),
    ("large", "l", "Large"),
    ("hiera_l", "l", "Large"),
)

_SAM1_ARCHITECTURES = (
    ("sam_vit_h", "SAM ViT-H"),
    ("sam_vit_l", "SAM ViT-L"),
    ("sam_vit_b", "SAM ViT-B"),
    ("sam_vit_t", "SAM ViT-T"),
)


def sam_model_spec_from_path(path: Path) -> SamModelSpec | None:
    checkpoint = Path(path)
    name = checkpoint.name.lower()
    if checkpoint.suffix.lower() != ".pt" or not name.startswith("sam"):
        return None

    normalized_stem = checkpoint.stem.lower()
    if normalized_stem == "sam3":
        return SamModelSpec(
            key=checkpoint.name,
            display_name="SAM 3",
            checkpoint_path=checkpoint.resolve(),
            config_name="",
            runtime_kind="sam3",
        )

    sam2_match = re.match(r"^sam2(?:[._-]?1)?[_-]hiera[_-]", normalized_stem)
    if sam2_match:
        architecture = next(
            (
                (config_suffix, display_suffix)
                for marker, config_suffix, display_suffix in _ARCHITECTURES
                if normalized_stem.endswith(marker)
                and len(normalized_stem) > len(marker)
                and normalized_stem[-len(marker) - 1] in "_.-"
            ),
            None,
        )
        if architecture is not None:
            config_suffix, display_suffix = architecture
            is_sam21 = bool(re.match(r"^sam2[._-]?1[_-]", normalized_stem))
            version = "sam2.1" if is_sam21 else "sam2"
            config_name = f"configs/{version}/{version}_hiera_{config_suffix}.yaml"
            display_version = "SAM 2.1" if is_sam21 else "SAM 2"
            return SamModelSpec(
                key=checkpoint.name,
                display_name=f"{display_version} {display_suffix}",
                checkpoint_path=checkpoint.resolve(),
                config_name=config_name,
                runtime_kind="sam2",
            )

    sam1_display_name = next(
        (
            display_name
            for marker, display_name in _SAM1_ARCHITECTURES
            if re.fullmatch(rf"{re.escape(marker)}(?:_[0-9a-f]{{6}})?", normalized_stem)
        ),
        None,
    )
    if sam1_display_name is not None:
        return SamModelSpec(
            key=checkpoint.name,
            display_name=sam1_display_name,
            checkpoint_path=checkpoint.resolve(),
            config_name="",
        )

    # A user-renamed checkpoint is still useful to show, but its architecture
    # cannot be inferred safely from the filename.
    return SamModelSpec(
        key=checkpoint.name,
        display_name=checkpoint.name,
        checkpoint_path=checkpoint.resolve(),
        config_name="",
    )


def find_sam_model_specs(
    project_root: Path,
    app_root: Path | None = None,
) -> list[SamModelSpec]:
    roots = [Path(project_root).resolve()]
    resolved_app_root = Path(ROOT if app_root is None else app_root).resolve()
    if resolved_app_root not in roots:
        roots.append(resolved_app_root)

    specs: list[SamModelSpec] = []
    seen_names: set[str] = set()
    for root in roots:
        models_dir = root / "data" / "models"
        if not models_dir.is_dir():
            continue
        for path in sorted(models_dir.glob("*.pt"), key=lambda item: item.name.lower()):
            normalized_name = path.name.lower()
            if normalized_name in seen_names:
                continue
            spec = sam_model_spec_from_path(path)
            if spec is None:
                continue
            specs.append(spec)
            seen_names.add(normalized_name)
    return specs


def preferred_sam_model(
    specs: list[SamModelSpec], saved_model_path: str = ""
) -> SamModelSpec | None:
    if not specs:
        return None
    saved_name = Path(str(saved_model_path or "")).name.lower()
    if saved_name:
        for spec in specs:
            if spec.checkpoint_path.name.lower() == saved_name:
                return spec
    preferred_name = "sam2.1_hiera_base_plus.pt"
    return next(
        (spec for spec in specs if spec.checkpoint_path.name.lower() == preferred_name),
        specs[0],
    )


def sam_geometry_from_mask(
    mask: Any,
    score: float,
    *,
    minimum_area: float = 4.0,
    simplification_ratio: float = 0.002,
) -> SamAssistGeometry | None:
    import cv2
    import numpy as np

    binary = (np.asarray(mask) > 0.5).astype(np.uint8) * 255
    if binary.ndim != 2:
        return None
    contours, _hierarchy = cv2.findContours(
        binary,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )
    if not contours:
        return None
    # Use foreground pixels for the threshold so the setting means mask area
    # in pixels, including thin or small instances whose contour area is lower.
    if float(np.count_nonzero(binary)) < float(minimum_area):
        return None
    contour = max(contours, key=cv2.contourArea)

    perimeter = float(cv2.arcLength(contour, True))
    epsilon = max(0.5, perimeter * max(0.0, float(simplification_ratio)))
    approximation = cv2.approxPolyDP(contour, epsilon, True)
    polygon = [tuple(map(float, point)) for point in approximation.reshape(-1, 2)]
    if len(polygon) < 3:
        return None

    x, y, width, height = cv2.boundingRect(contour)
    rectangle = [
        (float(x), float(y)),
        (float(x + width), float(y)),
        (float(x + width), float(y + height)),
        (float(x), float(y + height)),
    ]
    box = cv2.boxPoints(cv2.minAreaRect(contour))
    oriented_rectangle = _canonical_clockwise_points(box)
    if len(oriented_rectangle) != 4:
        return None
    return SamAssistGeometry(
        polygon=polygon,
        rectangle=rectangle,
        oriented_rectangle=oriented_rectangle,
        score=float(score),
    )


def _canonical_clockwise_points(points: Any) -> list[tuple[float, float]]:
    values = [tuple(map(float, point)) for point in points]
    if not values:
        return []
    center_x = sum(point[0] for point in values) / len(values)
    center_y = sum(point[1] for point in values) / len(values)
    ordered = sorted(
        values,
        key=lambda point: math.atan2(point[1] - center_y, point[0] - center_x),
    )
    start = min(range(len(ordered)), key=lambda index: (ordered[index][1], ordered[index][0]))
    return ordered[start:] + ordered[:start]


__all__ = [
    "SamAssistGeometry",
    "SamModelSpec",
    "find_sam_model_specs",
    "preferred_sam_model",
    "sam_geometry_from_mask",
    "sam_model_spec_from_path",
]
