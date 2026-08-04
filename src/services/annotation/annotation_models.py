from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EditableAnnotation:
    class_id: int
    shape: str
    points: list[tuple[float, float]]
    radius_point: tuple[float, float] | None = None


__all__ = ["EditableAnnotation"]
