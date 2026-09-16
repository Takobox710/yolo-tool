from __future__ import annotations

from src.shared.qt import (
    QCheckBox,
    QEvent,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QSize,
    QSizePolicy,
    Qt,
    QVBoxLayout,
    QWidget,
)
from src.ui.shared.theme import current_theme_mode


ANNOTATION_CHECKED_ROLE = Qt.ItemDataRole.UserRole + 1
ANNOTATION_UNSAVED_ROLE = Qt.ItemDataRole.UserRole + 2
ANNOTATION_DISPLAY_TEXT_ROLE = Qt.ItemDataRole.UserRole + 3
ANNOTATION_UNSAVED_TEXT_ROLE = Qt.ItemDataRole.UserRole + 4
FILE_ITEM_LIGHT_HEIGHT = 28
FILE_ITEM_DARK_HEIGHT = 36


class AnnotationFileListItemWidget(QWidget):
    def __init__(self, item: QListWidgetItem, parent=None):
        super().__init__(parent)
        self._item = item
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 0, 4, 0)
        outer.setSpacing(0)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.checkbox = QCheckBox()
        self.checkbox.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.checkbox.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.checkbox, 0, Qt.AlignmentFlag.AlignVCenter)
        self.name_label = QLabel()
        self.name_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.name_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.name_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        layout.addWidget(self.name_label, 1)
        self.unsaved_label = QLabel("（未保存）")
        self.unsaved_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.unsaved_label.setObjectName("annotationUnsaved")
        self.unsaved_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.unsaved_label.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
        )
        layout.addWidget(self.unsaved_label, 0)
        layout.addStretch(1)
        outer.addStretch(1)
        outer.addLayout(layout)
        outer.addStretch(1)
        self.refresh_for_theme()
        self.sync_from_item()

    def _row_height(self) -> int:
        return (
            FILE_ITEM_DARK_HEIGHT
            if current_theme_mode() == "dark"
            else FILE_ITEM_LIGHT_HEIGHT
        )

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt API name
        hint = super().sizeHint()
        return QSize(hint.width(), self._row_height())

    def changeEvent(self, event) -> None:  # noqa: N802 - Qt API name
        super().changeEvent(event)
        if event.type() in {QEvent.Type.PaletteChange, QEvent.Type.StyleChange}:
            self.refresh_for_theme()

    def refresh_for_theme(self) -> None:
        row_height = self._row_height()
        self.setMinimumHeight(row_height)
        self.updateGeometry()
        self.update()

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
