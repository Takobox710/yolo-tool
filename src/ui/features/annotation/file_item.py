from __future__ import annotations

from src.shared.qt import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QSizePolicy,
    Qt,
    QWidget,
)


ANNOTATION_CHECKED_ROLE = Qt.ItemDataRole.UserRole + 1
ANNOTATION_UNSAVED_ROLE = Qt.ItemDataRole.UserRole + 2
ANNOTATION_DISPLAY_TEXT_ROLE = Qt.ItemDataRole.UserRole + 3
ANNOTATION_UNSAVED_TEXT_ROLE = Qt.ItemDataRole.UserRole + 4


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
        unsaved_text = self.unsavedText()
        self.unsaved_label.setText(f"（{unsaved_text}）" if unsaved_text else "")
        self.unsaved_label.setVisible(bool(unsaved_text))

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

    def unsavedText(self) -> str:
        value = self._item.data(ANNOTATION_UNSAVED_TEXT_ROLE)
        return "" if value is None else str(value)


__all__ = [
    "ANNOTATION_CHECKED_ROLE",
    "ANNOTATION_DISPLAY_TEXT_ROLE",
    "ANNOTATION_UNSAVED_ROLE",
    "ANNOTATION_UNSAVED_TEXT_ROLE",
    "AnnotationFileListItemWidget",
]
