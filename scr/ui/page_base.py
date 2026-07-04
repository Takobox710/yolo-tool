from __future__ import annotations

from pathlib import Path
from typing import Any

from scr.paths import ROOT
from scr.ui.helpers import _display_project_path, _history_number_sort_key, _history_time_sort_key, _resolve_project_path
from scr.ui.widgets.base import Card, ImageView
from scr.ui.qt import QCheckBox, QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QKeySequence, QLineEdit, QPushButton, QShortcut, QSizePolicy, QTableWidgetItem, Qt, QTextEdit, QVBoxLayout, QWidget


_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp"}


class _SortItem(QTableWidgetItem):
    def __init__(self, text: str, sort_key: float = 0.0):
        super().__init__(text)
        self.setData(Qt.ItemDataRole.UserRole, sort_key)

    def __lt__(self, other):
        if isinstance(other, QTableWidgetItem):
            a = self.data(Qt.ItemDataRole.UserRole)
            b = other.data(Qt.ItemDataRole.UserRole)
            if a is not None and b is not None:
                try:
                    return float(a) < float(b)
                except (ValueError, TypeError):
                    pass
        return super().__lt__(other)


class BasePage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app

    def project_root(self) -> Path:
        return Path(self.app.settings["project"]["root"])

    def save_settings(self):
        self.app.settings_service.save(self.app.settings)

    def update_setting(self, *keys: str, value: Any):
        if not keys:
            return
        target = self.app.settings
        for key in keys[:-1]:
            target = target.setdefault(key, {})
        target[keys[-1]] = value
        self.save_settings()

    def display_path(self, path: str | Path) -> str:
        return _display_project_path(str(path), self.project_root())

    def resolve_path_text(self, edit: QLineEdit) -> str:
        return _resolve_project_path(edit.text(), self.project_root())

    def path_from_edit(self, edit: QLineEdit) -> Path:
        return Path(self.resolve_path_text(edit))

    def page_layout(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)
        return layout

    def prepare_readonly_text(self, edit: QTextEdit):
        edit.setReadOnly(True)
        edit.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        edit.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        edit.setCursorWidth(0)
        edit.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        edit.customContextMenuRequested.connect(
            lambda pos, text_edit=edit: self._show_readonly_text_context_menu(
                text_edit, pos
            )
        )
        copy_shortcut = QShortcut(QKeySequence.StandardKey.Copy, edit)
        copy_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        copy_shortcut.activated.connect(lambda text_edit=edit: self._copy_readonly_text(text_edit))
        edit._copy_shortcut = copy_shortcut
        return edit

    def _copy_readonly_text(self, edit: QTextEdit):
        if not edit.isVisible():
            return
        if not edit.textCursor().hasSelection():
            return
        edit.copy()

    def _show_readonly_text_context_menu(self, edit: QTextEdit, pos):
        menu = edit.createStandardContextMenu()
        for action in menu.actions():
            text = action.text().replace("&", "")
            if "Copy" in text:
                action.setText("复制")
            elif "Select All" in text:
                action.setText("全选")
        menu.exec(edit.mapToGlobal(pos))

    def help_icons_enabled(self) -> bool:
        return bool(
            self.app.settings.get("features", {}).get("show_help_icons", True)
        )

    def refresh_help_icon_visibility(self):
        for label in self.findChildren(QLabel):
            self._refresh_help_target(label)
        for check in self.findChildren(QCheckBox):
            self._refresh_help_target(check)

    def dismiss_help_bubbles(self):
        return None

    def _set_help_target(self, widget, base_text: str, help_text: str):
        widget.setProperty("helpBaseText", base_text)
        widget.setProperty("helpText", help_text)
        self._refresh_help_target(widget)

    def _refresh_help_target(self, widget):
        base_text = widget.property("helpBaseText")
        help_text = widget.property("helpText")
        if base_text is None:
            return
        base_text = str(base_text)
        help_text = str(help_text or "")
        show_symbol = self.help_icons_enabled() and bool(help_text)
        widget.setText(f"{base_text} ⓘ" if show_symbol else base_text)
        widget.setToolTip(help_text)

    def _caption_widget(
        self,
        label: str,
        help_text: str = "",
        object_name: str = "fieldLabel",
        fixed_width: int | None = None,
    ):
        box = QWidget()
        layout = QHBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        caption = QLabel(label)
        caption.setObjectName(object_name)
        self._set_help_target(caption, label, help_text)
        layout.addWidget(caption)
        layout.addStretch(1)
        if fixed_width is not None:
            box.setFixedWidth(fixed_width)
        return box, caption, None

    def checkbox_with_help(
        self, text: str, checked: bool = False, help_text: str = ""
    ):
        box = QWidget()
        layout = QHBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        check = QCheckBox(text)
        check.setChecked(checked)
        self._set_help_target(check, text, help_text)
        layout.addWidget(check)
        layout.addStretch(1)
        return box, check

    def field(
        self,
        label: str,
        value: str = "",
        browse=None,
        placeholder: str = "",
        help_text: str = "",
    ):
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        caption_box, _caption, _icon = self._caption_widget(
            label, help_text=help_text, object_name="fieldLabel"
        )
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        edit = QLineEdit(str(value))
        if placeholder:
            edit.setPlaceholderText(placeholder)
        row.addWidget(edit, 1)
        if browse:
            button = QPushButton("选择")
            button.setObjectName("softButton")
            button.clicked.connect(lambda: browse(edit))
            row.addWidget(button)
        layout.addWidget(caption_box)
        layout.addLayout(row)
        return box, edit

    def path_field(
        self,
        label: str,
        value: str = "",
        browse=None,
        placeholder: str = "",
        help_text: str = "",
    ):
        return self.field(
            label,
            self.display_path(value),
            browse,
            placeholder,
            help_text=help_text,
        )

    def combo_field(
        self,
        label: str,
        value: str,
        values: list[str],
        help_text: str = "",
        *,
        editable: bool = False,
        placeholder: str = "",
    ):
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        caption_box, _caption, _icon = self._caption_widget(
            label, help_text=help_text, object_name="fieldLabel"
        )
        combo = QComboBox()
        combo.setEditable(editable)
        combo.addItems(values)
        if editable:
            self._configure_editable_combo(combo, placeholder)
        if str(value):
            combo.setCurrentText(str(value))
        layout.addWidget(caption_box)
        layout.addWidget(combo)
        return box, combo

    def inline_field(
        self,
        label: str,
        value: str = "",
        browse=None,
        placeholder: str = "",
        help_text: str = "",
        *,
        label_width: int = 88,
    ):
        box = QWidget()
        layout = QHBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        caption_box, _caption, _icon = self._caption_widget(
            label,
            help_text=help_text,
            object_name="inlineFieldLabel",
            fixed_width=label_width,
        )
        edit = QLineEdit(str(value))
        if placeholder:
            edit.setPlaceholderText(placeholder)
        layout.addWidget(caption_box)
        layout.addWidget(edit, 1)
        if browse:
            button = QPushButton("选择")
            button.setObjectName("softButton")
            button.clicked.connect(lambda: browse(edit))
            layout.addWidget(button)
        return box, edit

    def inline_combo_field(
        self,
        label: str,
        value: str,
        values: list[str],
        help_text: str = "",
        *,
        editable: bool = False,
        placeholder: str = "",
        label_width: int = 88,
    ):
        box = QWidget()
        layout = QHBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        caption_box, _caption, _icon = self._caption_widget(
            label,
            help_text=help_text,
            object_name="inlineFieldLabel",
            fixed_width=label_width,
        )
        combo = QComboBox()
        combo.setEditable(editable)
        combo.addItems(values)
        if editable:
            self._configure_editable_combo(combo, placeholder)
        if str(value):
            combo.setCurrentText(str(value))
        layout.addWidget(caption_box)
        layout.addWidget(combo, 1)
        return box, combo

    def stacked_field(
        self,
        label: str,
        value: str = "",
        browse=None,
        placeholder: str = "",
        help_text: str = "",
    ):
        box = QWidget()
        outer = QVBoxLayout(box)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)
        caption_box, _caption, _icon = self._caption_widget(
            label, help_text=help_text, object_name="fieldLabel"
        )
        outer.addWidget(caption_box)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        edit = QLineEdit(str(value))
        if placeholder:
            edit.setPlaceholderText(placeholder)
        row.addWidget(edit, 1)
        if browse:
            btn = QPushButton("选择")
            btn.setObjectName("softButton")
            btn.clicked.connect(lambda: browse(edit))
            row.addWidget(btn)
        outer.addLayout(row)
        return box, edit

    def stacked_path_field(
        self,
        label: str,
        value: str = "",
        browse=None,
        placeholder: str = "",
        help_text: str = "",
    ):
        return self.stacked_field(
            label,
            self.display_path(value),
            browse,
            placeholder,
            help_text=help_text,
        )

    def stacked_combo_field(
        self,
        label: str,
        value: str,
        values: list[str],
        browse=None,
        placeholder: str = "",
        help_text: str = "",
    ):
        box = QWidget()
        outer = QVBoxLayout(box)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)
        caption_box, _caption, _icon = self._caption_widget(
            label, help_text=help_text, object_name="fieldLabel"
        )
        outer.addWidget(caption_box)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        combo = QComboBox()
        combo.setEditable(True)
        combo.addItems(values)
        self._configure_editable_combo(combo, placeholder)
        if str(value):
            combo.setCurrentText(str(value))
        row.addWidget(combo, 1)
        if browse:
            btn = QPushButton("选择")
            btn.setObjectName("softButton")
            btn.clicked.connect(lambda: browse(combo))
            row.addWidget(btn)
        outer.addLayout(row)
        return box, combo

    def _configure_editable_combo(
        self, combo: QComboBox, placeholder: str = ""
    ) -> None:
        line_edit = combo.lineEdit()
        if line_edit is None:
            return
        line_edit.setFrame(False)
        line_edit.setContentsMargins(0, 0, 0, 0)
        line_edit.setTextMargins(0, 0, 0, 0)
        line_edit.setStyleSheet(
            "QLineEdit { background: transparent; border: 0; padding: 0; margin: 0; }"
        )
        if placeholder:
            line_edit.setPlaceholderText(placeholder)

    def choose_dir(self, edit: QLineEdit):
        current = self.resolve_path_text(edit) if edit.text() else str(self.project_root())
        path = QFileDialog.getExistingDirectory(self, "选择文件夹", current)
        if path:
            edit.setText(self.display_path(path))

    def choose_file(self, edit: QLineEdit, caption: str = "选择文件"):
        current = self.resolve_path_text(edit) if edit.text() else str(self.project_root())
        path, _ = QFileDialog.getOpenFileName(self, caption, current, "All Files (*)")
        if path:
            edit.setText(self.display_path(path))

    def _choose_pt_for_combo(self, combo: QComboBox):
        models_dir = self.project_root() / "data" / "models"
        models_dir.mkdir(parents=True, exist_ok=True)
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择模型文件",
            str(models_dir),
            "PyTorch 模型 (*.pt);;所有文件 (*)",
        )
        if path:
            combo.setCurrentText(self.display_path(path))

    def stat_card(self, label: str, value: str = "-"):
        card = QFrame()
        card.setObjectName("statCard")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)
        name = QLabel(label)
        name.setObjectName("fieldLabel")
        name.setFixedWidth(90)
        metric = QLabel(value)
        metric.setObjectName("statValue")
        metric.setWordWrap(False)
        metric.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        metric.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        layout.addWidget(name)
        layout.addWidget(metric, 1)
        return card, metric

    def metric_card(self, label: str, value: str = "待检测"):
        card = QFrame()
        card.setObjectName("metricCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        name = QLabel(label)
        name.setObjectName("fieldLabel")
        metric = QLabel(value)
        metric.setObjectName("metricValue")
        metric.setWordWrap(True)
        layout.addWidget(name)
        layout.addWidget(metric)
        return card, metric

    def short_gpu_name(self, name: str):
        cleaned = str(name or "").replace("NVIDIA GeForce ", "").replace("NVIDIA ", "").replace(" Laptop GPU", "")
        cleaned = cleaned.replace("RTX", "RTX ").replace("  ", " ").strip()
        return cleaned or "待检测"
