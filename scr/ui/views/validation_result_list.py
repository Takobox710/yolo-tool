from __future__ import annotations

from pathlib import Path
from typing import Callable

from scr.ui.qt import (
    QDialog,
    QDialogButtonBox,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QVBoxLayout,
)


def show_validation_result_list(
    *,
    parent,
    source_items: list[Path],
    source_index: int,
    set_source_index: Callable[[int], None],
    show_cached_source_result: Callable[[Path], bool],
) -> None:
    if not source_items:
        QMessageBox.information(
            parent, "输入源列表", "当前输入源没有可选择的图片或视频。"
        )
        return
    dialog = QDialog(parent)
    dialog.setWindowTitle("输入源列表")
    dialog.resize(320, 520)
    dialog.setMinimumSize(200, 200)
    layout = QVBoxLayout(dialog)
    listing = QListWidget()
    layout.addWidget(listing, 1)
    search = QLineEdit()
    search.setPlaceholderText("搜索文件名")
    layout.addWidget(search)
    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok
        | QDialogButtonBox.StandardButton.Cancel
    )
    layout.addWidget(buttons)
    visible_paths: list[Path] = []

    def filter_items(text: str = "") -> None:
        nonlocal visible_paths
        needle = text.strip().lower()
        visible_paths = [
            path
            for path in source_items
            if not needle or needle in path.name.lower()
        ]
        listing.clear()
        for path in visible_paths:
            listing.addItem(path.name)
        if visible_paths:
            current_path = (
                source_items[source_index]
                if 0 <= source_index < len(source_items)
                else visible_paths[0]
            )
            current_row = (
                visible_paths.index(current_path)
                if current_path in visible_paths
                else 0
            )
            listing.setCurrentRow(current_row)

    def jump_to_current() -> None:
        row = listing.currentRow()
        if 0 <= row < len(visible_paths):
            path = visible_paths[row]
            set_source_index(source_items.index(path))
            show_cached_source_result(path)
        dialog.accept()

    filter_items()
    search.textChanged.connect(filter_items)
    listing.itemDoubleClicked.connect(lambda _item: jump_to_current())
    buttons.accepted.connect(jump_to_current)
    buttons.rejected.connect(dialog.reject)
    dialog.exec()
