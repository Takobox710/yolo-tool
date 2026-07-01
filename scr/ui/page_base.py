from __future__ import annotations

from pathlib import Path

from scr.paths import ROOT
from scr.ui.helpers import _display_project_path, _history_number_sort_key, _history_time_sort_key, _resolve_project_path
from scr.ui.widgets.base import Card, ImageView
from scr.ui.qt import QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSizePolicy, QTableWidgetItem, Qt, QVBoxLayout, QWidget


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

    def field(self, label: str, value: str = "", browse=None, placeholder: str = ""):
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        caption = QLabel(label)
        caption.setObjectName("fieldLabel")
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
        layout.addWidget(caption)
        layout.addLayout(row)
        return box, edit

    def path_field(self, label: str, value: str = "", browse=None, placeholder: str = ""):
        return self.field(label, self.display_path(value), browse, placeholder)

    def combo_field(self, label: str, value: str, values: list[str]):
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        caption = QLabel(label)
        caption.setObjectName("fieldLabel")
        combo = QComboBox()
        combo.addItems(values)
        if value in values:
            combo.setCurrentText(value)
        layout.addWidget(caption)
        layout.addWidget(combo)
        return box, combo

    def inline_field(self, label: str, value: str = "", browse=None, placeholder: str = ""):
        box = QWidget()
        layout = QHBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        caption = QLabel(label)
        caption.setObjectName("inlineFieldLabel")
        caption.setFixedWidth(88)
        edit = QLineEdit(str(value))
        if placeholder:
            edit.setPlaceholderText(placeholder)
        layout.addWidget(caption)
        layout.addWidget(edit, 1)
        if browse:
            button = QPushButton("选择")
            button.setObjectName("softButton")
            button.clicked.connect(lambda: browse(edit))
            layout.addWidget(button)
        return box, edit

    def inline_combo_field(self, label: str, value: str, values: list[str]):
        box = QWidget()
        layout = QHBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        caption = QLabel(label)
        caption.setObjectName("inlineFieldLabel")
        caption.setFixedWidth(88)
        combo = QComboBox()
        combo.addItems(values)
        if value in values:
            combo.setCurrentText(value)
        layout.addWidget(caption)
        layout.addWidget(combo, 1)
        return box, combo

    def stacked_field(self, label: str, value: str = "", browse=None, placeholder: str = ""):
        box = QWidget()
        outer = QVBoxLayout(box)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)
        lbl = QLabel(label)
        lbl.setObjectName("fieldLabel")
        outer.addWidget(lbl)
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

    def stacked_path_field(self, label: str, value: str = "", browse=None, placeholder: str = ""):
        return self.stacked_field(label, self.display_path(value), browse, placeholder)

    def stacked_combo_field(self, label: str, value: str, values: list[str], browse=None, placeholder: str = ""):
        box = QWidget()
        outer = QVBoxLayout(box)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)
        lbl = QLabel(label)
        lbl.setObjectName("fieldLabel")
        outer.addWidget(lbl)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        combo = QComboBox()
        combo.setEditable(True)
        combo.addItems(values)
        if placeholder and combo.lineEdit():
            combo.lineEdit().setPlaceholderText(placeholder)
        if value in values:
            combo.setCurrentText(value)
        row.addWidget(combo, 1)
        if browse:
            btn = QPushButton("选择")
            btn.setObjectName("softButton")
            btn.clicked.connect(lambda: browse(combo))
            row.addWidget(btn)
        outer.addLayout(row)
        return box, combo

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
        path, _ = QFileDialog.getOpenFileName(self, "选择模型文件", str(ROOT), "PyTorch 模型 (*.pt);;所有文件 (*)")
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
