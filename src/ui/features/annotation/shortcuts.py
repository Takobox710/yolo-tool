from __future__ import annotations

from PySide6.QtGui import QKeySequence

from src.shared.qt import QShortcut, Qt


def register_annotation_shortcuts(page) -> None:
    delete_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Delete), page)
    delete_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
    delete_shortcut.activated.connect(page.delete_selected)
    page._delete_shortcut = delete_shortcut

    save_shortcut = QShortcut(QKeySequence.StandardKey.Save, page)
    save_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
    save_shortcut.activated.connect(page.save_current_default)
    page._save_shortcut = save_shortcut

    save_yolo_shortcut = QShortcut(QKeySequence("Ctrl+Shift+S"), page)
    save_yolo_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
    save_yolo_shortcut.activated.connect(page.save_current_yolo)
    page._save_yolo_shortcut = save_yolo_shortcut
