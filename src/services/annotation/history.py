from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.services.annotation.editable_document import EditableAnnotation


@dataclass(frozen=True, slots=True)
class AnnotationValue:
    class_id: int
    shape: str
    points: tuple[tuple[float, float], ...]
    radius_point: tuple[float, float] | None

    @classmethod
    def from_annotation(cls, annotation: EditableAnnotation) -> "AnnotationValue":
        return cls(
            class_id=int(annotation.class_id),
            shape=str(annotation.shape),
            points=tuple((float(x), float(y)) for x, y in annotation.points),
            radius_point=(
                None
                if annotation.radius_point is None
                else (
                    float(annotation.radius_point[0]),
                    float(annotation.radius_point[1]),
                )
            ),
        )

    def to_annotation(self) -> EditableAnnotation:
        return EditableAnnotation(
            self.class_id,
            self.shape,
            list(self.points),
            self.radius_point,
        )


def snapshot_annotations(
    annotations: list[EditableAnnotation],
) -> tuple[AnnotationValue, ...]:
    return tuple(AnnotationValue.from_annotation(annotation) for annotation in annotations)


def restore_annotations(
    values: tuple[AnnotationValue, ...],
) -> list[EditableAnnotation]:
    return [value.to_annotation() for value in values]


@dataclass(frozen=True, slots=True)
class AnnotationHistoryEntry:
    image_path: Path
    before: tuple[AnnotationValue, ...]
    after: tuple[AnnotationValue, ...]
    focus_index: int | None


class AnnotationHistory:
    def __init__(self, limit: int = 5):
        self.limit = max(1, int(limit))
        self._undo: list[AnnotationHistoryEntry] = []
        self._redo: list[AnnotationHistoryEntry] = []

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def clear(self) -> None:
        self._undo.clear()
        self._redo.clear()

    def record(
        self,
        image_path: Path,
        before: list[EditableAnnotation],
        after: list[EditableAnnotation],
        focus_index: int | None,
    ) -> bool:
        before_value = snapshot_annotations(before)
        after_value = snapshot_annotations(after)
        if before_value == after_value:
            return False
        self._undo.append(
            AnnotationHistoryEntry(
                Path(image_path),
                before_value,
                after_value,
                focus_index,
            )
        )
        del self._undo[:-self.limit]
        self._redo.clear()
        return True

    def pop_undo(self) -> AnnotationHistoryEntry | None:
        if not self._undo:
            return None
        entry = self._undo.pop()
        self._redo.append(entry)
        return entry

    def pop_redo(self) -> AnnotationHistoryEntry | None:
        if not self._redo:
            return None
        entry = self._redo.pop()
        self._undo.append(entry)
        return entry


__all__ = [
    "AnnotationHistory",
    "AnnotationHistoryEntry",
    "AnnotationValue",
    "restore_annotations",
    "snapshot_annotations",
]
