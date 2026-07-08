from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QPoint, QTimer

from src.shared.qt import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    Qt,
    QVBoxLayout,
)


class CustomAiImageSelectionDialog(QDialog):
    def __init__(
        self,
        image_items: list[Path],
        selected_images: list[Path] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("自定义图片列表")
        self.resize(360, 560)
        self.setMinimumSize(220, 240)
        self.image_items = list(image_items)
        self.selected_paths = {
            Path(path).resolve() for path in (selected_images or [])
        }
        self.visible_paths: list[Path] = []
        self.checkboxes: dict[Path, QCheckBox] = {}
        self._drag_select_active = False
        self._drag_select_state = False
        self._drag_last_row = -1
        self._drag_viewport_pos = QPoint()
        self._auto_scroll_direction = 0
        self._auto_scroll_step = 0
        self._auto_scroll_timer = QTimer(self)
        self._auto_scroll_timer.setInterval(30)
        self._auto_scroll_timer.timeout.connect(self._perform_auto_scroll_step)

        layout = QVBoxLayout(self)
        self.listing = QListWidget()
        self.listing.itemClicked.connect(self.toggle_item_from_row)
        self.listing.viewport().installEventFilter(self)
        layout.addWidget(self.listing, 1)

        bulk_row = QHBoxLayout()
        bulk_row.setContentsMargins(0, 0, 0, 0)
        bulk_row.setSpacing(8)
        select_all_btn = QPushButton("全选")
        select_all_btn.clicked.connect(self.select_all_visible)
        bulk_row.addWidget(select_all_btn)
        invert_btn = QPushButton("反选")
        invert_btn.clicked.connect(self.invert_visible_selection)
        bulk_row.addWidget(invert_btn)
        clear_btn = QPushButton("全不选")
        clear_btn.clicked.connect(self.clear_visible_selection)
        bulk_row.addWidget(clear_btn)
        bulk_row.addStretch(1)
        layout.addLayout(bulk_row)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索文件名")
        self.search_edit.textChanged.connect(self.refresh_items)
        layout.addWidget(self.search_edit)

        footer_row = QHBoxLayout()
        footer_row.setContentsMargins(0, 0, 0, 0)
        footer_row.setSpacing(8)
        self.selected_count_label = QLabel("")
        self.selected_count_label.setObjectName("fieldLabel")
        footer_row.addWidget(self.selected_count_label)
        footer_row.addStretch(1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        footer_row.addWidget(buttons)
        layout.addLayout(footer_row)
        self.refresh_items()

    def _set_path_selected(self, path: Path, checked: bool) -> None:
        resolved = Path(path).resolve()
        if checked:
            self.selected_paths.add(resolved)
        else:
            self.selected_paths.discard(resolved)
        self._refresh_selected_count_label()

    def _refresh_selected_count_label(self) -> None:
        if hasattr(self, "selected_count_label"):
            self.selected_count_label.setText(f"已选择 {len(self.selected_paths)} 张图片")

    def refresh_items(self, text: str = "") -> None:
        needle = text.strip().lower()
        self.visible_paths = [
            path
            for path in self.image_items
            if not needle or needle in path.name.lower()
        ]
        self.checkboxes = {}
        self.listing.clear()
        for path in self.visible_paths:
            resolved = Path(path).resolve()
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, str(resolved))
            checkbox = QCheckBox(path.name)
            checkbox.setChecked(resolved in self.selected_paths)
            checkbox.toggled.connect(
                lambda checked, current_path=path: self._set_path_selected(
                    current_path, checked
                )
            )
            self.listing.addItem(item)
            self.listing.setItemWidget(item, checkbox)
            item.setSizeHint(checkbox.sizeHint())
            self.checkboxes[resolved] = checkbox
        self._refresh_selected_count_label()

    def toggle_item_from_row(self, item: QListWidgetItem) -> None:
        raw_path = str(item.data(Qt.ItemDataRole.UserRole) or "")
        if not raw_path:
            return
        checkbox = self.checkboxes.get(Path(raw_path).resolve())
        if checkbox is not None:
            checkbox.toggle()

    def _set_item_checked(self, item: QListWidgetItem, checked: bool) -> None:
        raw_path = str(item.data(Qt.ItemDataRole.UserRole) or "")
        if not raw_path:
            return
        resolved = Path(raw_path).resolve()
        checkbox = self.checkboxes.get(resolved)
        if checkbox is not None:
            checkbox.setChecked(checked)
        else:
            self._set_path_selected(Path(raw_path), checked)

    def _item_from_viewport_pos(self, pos) -> QListWidgetItem | None:
        item = self.listing.itemAt(pos)
        return item if item is not None else None

    def _clamped_viewport_pos(self, pos: QPoint) -> QPoint:
        viewport = self.listing.viewport()
        x_pos = min(max(0, pos.x()), max(0, viewport.width() - 1))
        y_pos = min(max(0, pos.y()), max(0, viewport.height() - 1))
        return QPoint(x_pos, y_pos)

    def _row_for_item(self, item: QListWidgetItem | None) -> int:
        if item is None:
            return -1
        return self.listing.row(item)

    def _apply_drag_selection_to_row(self, row: int) -> None:
        if row < 0:
            return
        if self._drag_last_row < 0:
            start_row = row
            end_row = row
        else:
            start_row = min(self._drag_last_row, row)
            end_row = max(self._drag_last_row, row)
        for current_row in range(start_row, end_row + 1):
            item = self.listing.item(current_row)
            if item is not None:
                self._set_item_checked(item, self._drag_select_state)
        self._drag_last_row = row

    def _update_auto_scroll(self, pos: QPoint) -> None:
        viewport = self.listing.viewport()
        edge_threshold = 36
        direction = 0
        step = 0
        if pos.y() < edge_threshold:
            depth = edge_threshold - pos.y()
            ratio = min(1.0, depth / edge_threshold)
            direction = -1
            step = max(1, int(1 + ratio * 7))
        elif pos.y() > max(0, viewport.height() - edge_threshold):
            depth = pos.y() - max(0, viewport.height() - edge_threshold)
            ratio = min(1.0, depth / edge_threshold)
            direction = 1
            step = max(1, int(1 + ratio * 7))

        self._auto_scroll_direction = direction
        self._auto_scroll_step = step
        if direction == 0:
            self._auto_scroll_timer.stop()
        elif not self._auto_scroll_timer.isActive():
            self._auto_scroll_timer.start()

    def _stop_drag_auto_scroll(self) -> None:
        self._auto_scroll_timer.stop()
        self._auto_scroll_direction = 0
        self._auto_scroll_step = 0

    def _apply_drag_selection_from_pos(self, pos: QPoint) -> None:
        self._drag_viewport_pos = QPoint(pos)
        item = self._item_from_viewport_pos(self._clamped_viewport_pos(pos))
        if item is not None:
            self._apply_drag_selection_to_row(self._row_for_item(item))
        self._update_auto_scroll(pos)

    def _perform_auto_scroll_step(self) -> None:
        if not self._drag_select_active or self._auto_scroll_direction == 0:
            self._stop_drag_auto_scroll()
            return
        scrollbar = self.listing.verticalScrollBar()
        previous_value = scrollbar.value()
        scrollbar.setValue(
            previous_value + self._auto_scroll_direction * self._auto_scroll_step
        )
        if scrollbar.value() == previous_value:
            self._stop_drag_auto_scroll()
            return
        item = self._item_from_viewport_pos(
            self._clamped_viewport_pos(self._drag_viewport_pos)
        )
        if item is not None:
            self._apply_drag_selection_to_row(self._row_for_item(item))

    def eventFilter(self, watched, event):
        if watched is self.listing.viewport():
            if event.type() == QEvent.Type.MouseButtonPress:
                pos = event.position().toPoint()
                item = self._item_from_viewport_pos(self._clamped_viewport_pos(pos))
                if item is not None and event.button() == Qt.MouseButton.LeftButton:
                    raw_path = str(item.data(Qt.ItemDataRole.UserRole) or "")
                    checkbox = self.checkboxes.get(Path(raw_path).resolve()) if raw_path else None
                    if checkbox is not None:
                        self._drag_select_active = True
                        self._drag_select_state = not checkbox.isChecked()
                        self._drag_last_row = -1
                        self._apply_drag_selection_from_pos(pos)
                        return True
            elif event.type() == QEvent.Type.MouseMove and self._drag_select_active:
                self._apply_drag_selection_from_pos(event.position().toPoint())
                return True
            elif event.type() == QEvent.Type.MouseButtonRelease and self._drag_select_active:
                self._drag_select_active = False
                self._drag_last_row = -1
                self._stop_drag_auto_scroll()
                return True
        return super().eventFilter(watched, event)

    def _apply_visible_selection(self, resolver) -> None:
        for path in self.visible_paths:
            resolved = Path(path).resolve()
            checkbox = self.checkboxes.get(resolved)
            checked = resolver(resolved)
            if checkbox is not None:
                checkbox.setChecked(checked)
            else:
                self._set_path_selected(path, checked)

    def select_all_visible(self) -> None:
        self._apply_visible_selection(lambda _path: True)

    def invert_visible_selection(self) -> None:
        self._apply_visible_selection(
            lambda current_path: current_path not in self.selected_paths
        )

    def clear_visible_selection(self) -> None:
        self._apply_visible_selection(lambda _path: False)

    def selected_image_paths(self) -> list[Path]:
        return [
            path
            for path in self.image_items
            if Path(path).resolve() in self.selected_paths
        ]


