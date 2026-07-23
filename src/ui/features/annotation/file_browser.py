from __future__ import annotations

from pathlib import Path

from src.services.annotation import collect_annotation_presence, scan_annotation_image_items
from src.shared.qt import (
    QAbstractItemView,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QSizePolicy,
    QStyle,
    Qt,
    QWidget,
)
from src.ui.shared.workers import Worker


ANNOTATION_CHECKED_ROLE = Qt.ItemDataRole.UserRole + 1
ANNOTATION_UNSAVED_ROLE = Qt.ItemDataRole.UserRole + 2
ANNOTATION_DISPLAY_TEXT_ROLE = Qt.ItemDataRole.UserRole + 3


class AnnotationFileListItemWidget(QWidget):
    def __init__(self, item: QListWidgetItem, parent=None):
        super().__init__(parent)
        self._item = item
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)
        self.checkbox = QCheckBox()
        self.checkbox.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.checkbox.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.checkbox)
        self.name_label = QLabel()
        self.name_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.name_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        layout.addWidget(self.name_label)
        self.unsaved_label = QLabel("（未保存）")
        self.unsaved_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.unsaved_label.setStyleSheet("color: #C62828;")
        layout.addWidget(self.unsaved_label)
        layout.addStretch(1)
        self.setMinimumHeight(28)
        self.sync_from_item()

    def sync_from_item(self) -> None:
        self.name_label.setText(self.text())
        self.checkbox.setChecked(self.isChecked())
        self.unsaved_label.setVisible(self.isUnsaved())

    def text(self) -> str:
        value = self._item.data(ANNOTATION_DISPLAY_TEXT_ROLE)
        return "" if value is None else str(value)

    def isChecked(self) -> bool:
        return bool(self._item.data(ANNOTATION_CHECKED_ROLE))

    def setChecked(self, checked: bool) -> None:
        self._item.setData(ANNOTATION_CHECKED_ROLE, bool(checked))
        self.checkbox.setChecked(bool(checked))

    def isUnsaved(self) -> bool:
        return bool(self._item.data(ANNOTATION_UNSAVED_ROLE))

    def setUnsaved(self, unsaved: bool) -> None:
        self._item.setData(ANNOTATION_UNSAVED_ROLE, bool(unsaved))
        self.unsaved_label.setVisible(bool(unsaved))


class AnnotationFileBrowserMixin:
    def _file_list_item_size_hint(self):
        return self.file_list.sizeHintForRow(0) and self.file_list.item(0).sizeHint()

    def _create_file_list_item(
        self, path: Path, *, checked: bool, unsaved: bool
    ) -> QListWidgetItem:
        item = self._list_widget_item_factory(path.name)
        item.setText("")
        item.setData(ANNOTATION_DISPLAY_TEXT_ROLE, path.name)
        item.setData(ANNOTATION_CHECKED_ROLE, bool(checked))
        item.setData(ANNOTATION_UNSAVED_ROLE, bool(unsaved))
        item.setSizeHint(self._standard_file_item_size_hint())
        return item

    def _standard_file_item_size_hint(self):
        if not hasattr(self, "_cached_file_item_size_hint"):
            sample_item = self._list_widget_item_factory("")
            sample_item.setData(ANNOTATION_DISPLAY_TEXT_ROLE, "sample.jpg")
            sample_item.setData(ANNOTATION_CHECKED_ROLE, False)
            sample_item.setData(ANNOTATION_UNSAVED_ROLE, False)
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

    def scan_images(self, *, select_first: bool) -> None:
        self._sync_project_labelme_class_names()
        image_dir = self.path_from_setting("images_dir")
        self.image_items = scan_annotation_image_items(image_dir)
        self._annotation_status_request_id += 1
        self._cancel_annotation_status_scan()
        self._file_list_render_timer.stop()
        self._annotation_statuses = {}
        if select_first and self.image_items:
            self.current_index = 0
        elif self.current_index >= len(self.image_items):
            self.current_index = 0 if self.image_items else -1
        initial_count = self._initial_file_render_count()
        sync_paths = self.image_items[:initial_count]
        if sync_paths:
            self._annotation_statuses.update(
                collect_annotation_presence(
                    sync_paths,
                    self.path_from_setting("annotations_dir"),
                    self.path_from_setting("labels_dir"),
                )
            )
        self.refresh_file_list()
        if self.current_index >= 0:
            self._ensure_file_list_items(self.current_index + 1)
            self.file_list.setCurrentRow(self.current_index)
            self.load_current()
        else:
            self._update_file_count_label()
            self.canvas.set_image(None, [], self.class_names())
        self._schedule_remaining_file_list_render()
        self._start_annotation_status_scan(self._annotation_status_request_id, sync_paths)
        self._refresh_manual_action_buttons()

    def prepare_initial_image(self) -> None:
        self._sync_project_labelme_class_names()
        if self.image_items:
            return
        image_dir = self.path_from_setting("images_dir")
        self.image_items = scan_annotation_image_items(image_dir)
        if not self.image_items:
            self.current_index = -1
            return
        self._annotation_status_request_id += 1
        self._cancel_annotation_status_scan()
        self._file_list_render_timer.stop()
        self.current_index = 0
        self._annotation_statuses = {}
        sync_paths = self.image_items[: self._initial_file_render_count()]
        if sync_paths:
            self._annotation_statuses.update(
                collect_annotation_presence(
                    sync_paths,
                    self.path_from_setting("annotations_dir"),
                    self.path_from_setting("labels_dir"),
                )
            )
        self.refresh_file_list()
        self.file_list.setCurrentRow(self.current_index)
        self.load_current()
        self._schedule_remaining_file_list_render()
        self._start_annotation_status_scan(
            self._annotation_status_request_id, sync_paths
        )

    def _has_annotation_for_image(self, image_path: Path) -> bool:
        cached = self._annotation_statuses.get(self._annotation_status_key(image_path))
        if cached is not None:
            return cached
        if self.current_image_path == image_path and bool(self.canvas.annotations):
            return True
        return False

    @staticmethod
    def _annotation_status_key(image_path: Path) -> str:
        return str(Path(image_path).resolve())

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
            item = self._create_file_list_item(
                path,
                checked=self._has_annotation_for_image(path),
                unsaved=path == self.current_image_path
                and self._current_image_has_unsaved_changes(),
            )
            self.file_list.addItem(item)
            self._file_list_rendered_count += 1
        self.file_list.blockSignals(False)

    def _start_annotation_status_scan(
        self, request_id: int, already_scanned_paths: list[Path]
    ) -> None:
        remaining_paths = self.image_items[len(already_scanned_paths) :]
        if not remaining_paths:
            return
        self._annotation_status_worker = Worker(
            "annotation_file_status",
            lambda request_id=request_id, paths=list(remaining_paths): {
                "request_id": request_id,
                "statuses": collect_annotation_presence(
                    paths,
                    self.path_from_setting("annotations_dir"),
                    self.path_from_setting("labels_dir"),
                ),
            },
        )
        self._annotation_status_worker.finished_with_payload.connect(
            self._handle_annotation_status_payload
        )
        self._annotation_status_worker.finished.connect(
            self._clear_annotation_status_worker
        )
        self._annotation_status_worker.start()

    def _handle_annotation_status_payload(self, kind: str, payload) -> None:
        if kind != "annotation_file_status":
            return
        if not isinstance(payload, dict):
            return
        if payload.get("request_id") != self._annotation_status_request_id:
            return
        self._annotation_statuses.update(payload.get("statuses") or {})
        self._apply_visible_annotation_statuses()

    def _apply_visible_annotation_statuses(self) -> None:
        for row in range(min(self._file_list_rendered_count, len(self.image_items))):
            item = self.file_list.item(row)
            if item is None:
                continue
            path = self.image_items[row]
            checked = self._has_annotation_for_image(path)
            if path == self.current_image_path and bool(self.canvas.annotations):
                checked = True
            item.setData(ANNOTATION_CHECKED_ROLE, checked)
            self._sync_visible_file_item_widget(row)

    def _clear_annotation_status_worker(self) -> None:
        self._annotation_status_worker = None

    def _cancel_annotation_status_scan(self) -> None:
        worker = self._annotation_status_worker
        if worker is None:
            return
        worker.finished_with_payload.disconnect(self._handle_annotation_status_payload)
        worker.finished.disconnect(self._clear_annotation_status_worker)
        worker.wait(50)
        self._annotation_status_worker = None

    def _update_file_count_label(self) -> None:
        total = len(self.image_items)
        current = self.current_index + 1 if 0 <= self.current_index < total else 0
        if hasattr(self, "file_count_label"):
            self.file_count_label.setText(f"{current}/{total}")

    def _current_image_has_annotations(self) -> bool:
        return bool(self.canvas.annotations)

    def _current_image_has_unsaved_changes(self) -> bool:
        return (
            self.current_image_path is not None
            and not self.labelme_auto_save_enabled()
            and self.dirty
        )

    def _update_current_file_list_item(self) -> None:
        if not hasattr(self, "file_list"):
            return
        if not (0 <= self.current_index < len(self.image_items)):
            return
        self._ensure_file_list_items(self.current_index + 1)
        item = self.file_list.item(self.current_index)
        if item is None:
            return
        item.setData(ANNOTATION_CHECKED_ROLE, self._current_image_has_annotations())
        item.setData(
            ANNOTATION_UNSAVED_ROLE, self._current_image_has_unsaved_changes()
        )
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
