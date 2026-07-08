from __future__ import annotations

import json
from pathlib import Path

from src.services.data_ops import natural_sort_key
from src.ui.shared.page_base import _IMAGE_SUFFIXES
from src.shared.qt import QCheckBox, QHBoxLayout, QLabel, Qt, QWidget


class AnnotationFileListItemWidget(QWidget):
    def __init__(self, file_name: str, *, checked: bool, unsaved: bool, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(bool(checked))
        self.checkbox.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.checkbox.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.checkbox)
        self.name_label = QLabel(file_name)
        self.name_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.name_label)
        self.unsaved_label = QLabel("（未保存）")
        self.unsaved_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.unsaved_label.setStyleSheet("color: #C62828;")
        self.unsaved_label.setVisible(bool(unsaved))
        layout.addWidget(self.unsaved_label)
        layout.addStretch(1)

    def text(self) -> str:
        return self.name_label.text()

    def isChecked(self) -> bool:
        return self.checkbox.isChecked()

    def setChecked(self, checked: bool) -> None:
        self.checkbox.setChecked(bool(checked))

    def isUnsaved(self) -> bool:
        return not self.unsaved_label.isHidden()

    def setUnsaved(self, unsaved: bool) -> None:
        self.unsaved_label.setVisible(bool(unsaved))


class AnnotationFileBrowserMixin:
    def scan_images(self, *, select_first: bool) -> None:
        image_dir = self.path_from_setting("images_dir")
        self.image_items = (
            sorted(
                [
                    path
                    for path in image_dir.iterdir()
                    if path.is_file() and path.suffix.lower() in _IMAGE_SUFFIXES
                ],
                key=natural_sort_key,
            )
            if image_dir.exists()
            else []
        )
        if select_first and self.image_items:
            self.current_index = 0
        elif self.current_index >= len(self.image_items):
            self.current_index = 0 if self.image_items else -1
        self.refresh_file_list()
        if self.current_index >= 0:
            self.file_list.setCurrentRow(self.current_index)
            self.load_current()
        else:
            self._update_file_count_label()
            self.canvas.set_image(None, [], self.class_names())
        self._refresh_manual_action_buttons()

    def _has_annotation_for_image(self, image_path: Path) -> bool:
        if self.current_image_path == image_path and bool(self.canvas.annotations):
            return True
        json_path = self.path_from_setting("annotations_dir") / f"{image_path.stem}.json"
        yolo_path = self.path_from_setting("labels_dir") / f"{image_path.stem}.txt"
        if json_path.exists():
            try:
                payload = json.loads(json_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return False
            return bool(payload.get("shapes"))
        if yolo_path.exists():
            try:
                return any(line.strip() for line in yolo_path.read_text(encoding="utf-8").splitlines())
            except OSError:
                return False
        return False

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
        item = self.file_list.item(self.current_index)
        if item is None:
            return
        widget = self.file_list.itemWidget(item)
        if isinstance(widget, AnnotationFileListItemWidget):
            widget.setChecked(self._current_image_has_annotations())
            widget.setUnsaved(self._current_image_has_unsaved_changes())

    def refresh_file_list(self) -> None:
        if not hasattr(self, "file_list"):
            return
        self.file_list.blockSignals(True)
        self.file_list.clear()
        for path in self.image_items:
            item = self._list_widget_item_factory()
            widget = AnnotationFileListItemWidget(
                path.name,
                checked=self._has_annotation_for_image(path),
                unsaved=path == self.current_image_path and self._current_image_has_unsaved_changes(),
                parent=self.file_list,
            )
            item.setSizeHint(widget.sizeHint())
            self.file_list.addItem(item)
            self.file_list.setItemWidget(item, widget)
        self.file_list.blockSignals(False)
        if 0 <= self.current_index < len(self.image_items):
            self.file_list.blockSignals(True)
            self.file_list.setCurrentRow(self.current_index)
            self.file_list.blockSignals(False)
        self._update_file_count_label()
        self._refresh_manual_action_buttons()
