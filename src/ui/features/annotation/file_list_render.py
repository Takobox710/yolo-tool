from __future__ import annotations

from pathlib import Path

from src.shared.qt import QCheckBox
from src.ui.features.annotation.file_item import (
    ANNOTATION_CHECKED_ROLE,
    ANNOTATION_DISPLAY_TEXT_ROLE,
    ANNOTATION_UNSAVED_ROLE,
    ANNOTATION_UNSAVED_TEXT_ROLE,
    AnnotationFileListItemWidget,
)


class AnnotationFileListRenderMixin:
    def _file_list_item_size_hint(self):
        return self.file_list.sizeHintForRow(0) and self.file_list.item(0).sizeHint()

    def _create_file_list_item(self, path: Path, *, checked: bool, unsaved: str):
        item = self._list_widget_item_factory(path.name)
        item.setText("")
        item.setData(ANNOTATION_DISPLAY_TEXT_ROLE, path.name)
        item.setData(ANNOTATION_CHECKED_ROLE, bool(checked))
        item.setData(ANNOTATION_UNSAVED_ROLE, bool(unsaved))
        item.setData(ANNOTATION_UNSAVED_TEXT_ROLE, unsaved)
        item.setSizeHint(self._standard_file_item_size_hint())
        return item

    def _standard_file_item_size_hint(self):
        if not hasattr(self, "_cached_file_item_size_hint"):
            sample_item = self._list_widget_item_factory("")
            sample_item.setData(ANNOTATION_DISPLAY_TEXT_ROLE, "sample.jpg")
            sample_item.setData(ANNOTATION_CHECKED_ROLE, False)
            sample_item.setData(ANNOTATION_UNSAVED_ROLE, False)
            sample_item.setData(ANNOTATION_UNSAVED_TEXT_ROLE, "")
            sample_widget = AnnotationFileListItemWidget(sample_item, parent=self.file_list)
            self._cached_file_item_size_hint = sample_widget.sizeHint()
            sample_widget.deleteLater()
        return self._cached_file_item_size_hint

    def _sync_visible_file_item_widget(self, row: int) -> None:
        item = self.file_list.item(row)
        if item is None:
            return
        widget = self.file_list.itemWidget(item)
        if isinstance(widget, AnnotationFileListItemWidget):
            widget.sync_from_item()

    def _decorate_visible_rows(self) -> None:
        if self.file_list.count() == 0:
            return
        viewport = self.file_list.viewport().rect()
        for row in range(self.file_list.count()):
            rect = self.file_list.visualItemRect(self.file_list.item(row))
            if rect.isValid() and rect.intersects(viewport):
                item = self.file_list.item(row)
                widget = self.file_list.itemWidget(item)
                if widget is None:
                    widget = AnnotationFileListItemWidget(item, parent=self.file_list)
                    item.setSizeHint(widget.sizeHint())
                    self.file_list.setItemWidget(item, widget)
                else:
                    self._sync_visible_file_item_widget(row)

    def _decorate_initial_rows(self) -> None:
        limit = min(self._file_list_rendered_count, self._file_list_batch_size)
        for row in range(limit):
            item = self.file_list.item(row)
            if item is None or self.file_list.itemWidget(item) is not None:
                continue
            widget = AnnotationFileListItemWidget(item, parent=self.file_list)
            item.setSizeHint(widget.sizeHint())
            self.file_list.setItemWidget(item, widget)

    def _initial_file_render_count(self) -> int:
        return min(len(self.image_items), self._file_list_batch_size)

    def _schedule_remaining_file_list_render(self) -> None:
        if self._file_list_rendered_count < len(self.image_items):
            self._file_list_render_timer.start()

    def _render_next_file_list_batch(self) -> None:
        previous_row = self.file_list.currentRow()
        self._render_file_list_items(self._file_list_rendered_count + self._file_list_batch_size)
        if self._file_list_rendered_count >= len(self.image_items):
            self._file_list_render_timer.stop()
        if previous_row >= 0 and previous_row < self.file_list.count():
            self.file_list.blockSignals(True)
            self.file_list.setCurrentRow(previous_row)
            self.file_list.blockSignals(False)
        self._decorate_visible_rows()

    def _ensure_file_list_items(self, minimum_count: int) -> None:
        if self._file_list_rendered_count >= minimum_count:
            return
        self._render_file_list_items(minimum_count)
        if self._file_list_rendered_count >= len(self.image_items):
            self._file_list_render_timer.stop()
        self._decorate_visible_rows()

    def _render_file_list_items(self, target_count: int) -> None:
        if not hasattr(self, "file_list"):
            return
        target_count = min(target_count, len(self.image_items))
        self.file_list.blockSignals(True)
        while self._file_list_rendered_count < target_count:
            path = self.image_items[self._file_list_rendered_count]
            item = self._create_file_list_item(path, checked=self._has_annotation_for_image(path), unsaved=self._current_image_unsaved_text() if path == self.current_image_path else "")
            self.file_list.addItem(item)
            self._file_list_rendered_count += 1
        self.file_list.blockSignals(False)

    def _update_file_count_label(self) -> None:
        total = len(self.image_items)
        current = self.current_index + 1 if 0 <= self.current_index < total else 0
        if hasattr(self, "file_count_label"):
            self.file_count_label.setText(f"{current}/{total}")

    def _update_current_file_list_item(self) -> None:
        if not hasattr(self, "file_list") or not (0 <= self.current_index < len(self.image_items)):
            return
        self._ensure_file_list_items(self.current_index + 1)
        item = self.file_list.item(self.current_index)
        if item is None:
            return
        item.setData(ANNOTATION_CHECKED_ROLE, self._current_image_has_annotations())
        item.setData(ANNOTATION_UNSAVED_ROLE, self._current_image_has_unsaved_changes())
        item.setData(ANNOTATION_UNSAVED_TEXT_ROLE, self._current_image_unsaved_text())
        self._sync_visible_file_item_widget(self.current_index)

    def refresh_file_list(self) -> None:
        if not hasattr(self, "file_list"):
            return
        self.file_list.blockSignals(True)
        self.file_list.clear()
        self._file_list_rendered_count = 0
        self.file_list.blockSignals(False)
        self._render_file_list_items(self._initial_file_render_count())
        if 0 <= self.current_index < len(self.image_items):
            self._ensure_file_list_items(self.current_index + 1)
        if 0 <= self.current_index < self._file_list_rendered_count:
            self.file_list.blockSignals(True)
            self.file_list.setCurrentRow(self.current_index)
            self.file_list.blockSignals(False)
        self._decorate_initial_rows()
        self._decorate_visible_rows()
        self._update_file_count_label()
        self._refresh_manual_action_buttons()


__all__ = ["AnnotationFileListRenderMixin"]
