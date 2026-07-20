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

    draw_shortcut = QShortcut(QKeySequence(Qt.Key.Key_W), page)
    draw_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
    draw_shortcut.activated.connect(page.enable_draw_mode)
    page._draw_shortcut = draw_shortcut

    def activate_shape(shape: str) -> None:
        if shape == "line_expand" and not page.canvas.line_expand_enabled:
            return
        page.canvas.set_draw_shape(shape)

    shape_shortcuts = {}
    for key, shape in (
        ("V", "select"),
        ("R", "rect"),
        ("O", "obb_single"),
        ("M", "obb_mirror"),
        ("P", "polygon"),
        ("C", "circle"),
        ("L", "line_expand"),
    ):
        shortcut = QShortcut(QKeySequence(key), page)
        shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        shortcut.activated.connect(lambda shape=shape: activate_shape(shape))
        shape_shortcuts[key] = shortcut
    page._shape_shortcuts = shape_shortcuts
