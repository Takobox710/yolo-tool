from __future__ import annotations

from src.services.annotation.history import restore_annotations, snapshot_annotations


class AnnotationCanvasHistoryMixin:
    def _begin_annotation_mutation(self, focus_index: int | None) -> None:
        if self._mutation_before is None:
            self._mutation_before = snapshot_annotations(self.annotations)
            self._mutation_focus_index = focus_index

    def _snapshot_annotations(self):
        return snapshot_annotations(self.annotations)

    def _commit_annotation_mutation(self, before, focus_index: int | None = None) -> bool:
        after = snapshot_annotations(self.annotations)
        if before == after:
            return False
        if self.changed_callback:
            self.changed_callback()
        if self.history_callback:
            self.history_callback(
                restore_annotations(before),
                restore_annotations(after),
                self._mutation_focus_index if focus_index is None else focus_index,
            )
        return True

    def _emit_annotation_mutation(self, before, focus_index: int | None = None) -> bool:
        try:
            return self._commit_annotation_mutation(before, focus_index)
        finally:
            self._mutation_before = None
            self._mutation_focus_index = None
