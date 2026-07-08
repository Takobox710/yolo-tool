from __future__ import annotations

from pathlib import Path
from typing import Any

from src.services.data_ops import display_project_path, resolve_project_path
from src.ui.shared.forms import FormPageMixin
from src.ui.helpers import _history_number_sort_key, _history_time_sort_key
from src.ui.shared.widgets.base import Card, ImageView
from src.shared.qt import (
    QCheckBox,
    QLabel,
    QKeySequence,
    QLineEdit,
    QShortcut,
    QTableWidgetItem,
    Qt,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


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


class BasePage(FormPageMixin, QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app

    def project_root(self) -> Path:
        return Path(self.app.settings["project"]["root"])

    def save_settings(self):
        self.app.settings_service.save(self.app.settings)

    def set_status_text(self, text: str) -> None:
        status = getattr(self.app, "status", None)
        if status is not None and hasattr(status, "setText"):
            status.setText(text)
            return
        status_bar = getattr(self.app, "statusBar", None)
        if callable(status_bar):
            status_bar().showMessage(text)

    def update_setting(self, *keys: str, value: Any):
        if not keys:
            return
        target = self.app.settings
        for key in keys[:-1]:
            target = target.setdefault(key, {})
        target[keys[-1]] = value
        self.save_settings()

    def display_path(self, path: str | Path) -> str:
        return display_project_path(str(path), self.project_root())

    def resolve_path_text(self, edit: QLineEdit) -> str:
        return resolve_project_path(edit.text(), self.project_root())

    def path_from_edit(self, edit: QLineEdit) -> Path:
        return Path(self.resolve_path_text(edit))

    def append_program_log(self, text: str, *, level: str | None = None) -> None:
        hook = getattr(self.app, "append_program_log", None)
        if callable(hook):
            hook(text, level=level or self.infer_log_level(text))

    def program_log_text(self) -> str:
        hook = getattr(self.app, "program_log_text", None)
        if callable(hook):
            return str(hook())
        return "等待程序日志..."

    @staticmethod
    def infer_log_level(text: str) -> str:
        content = str(text or "")
        if any(token in content for token in ("失败", "异常", "错误", "Traceback", "退出码")):
            return "ERROR"
        if any(token in content for token in ("停止", "警告", "warning")):
            return "WARN"
        return "INFO"

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

    def short_gpu_name(self, name: str):
        cleaned = str(name or "").replace("NVIDIA GeForce ", "").replace("NVIDIA ", "").replace(" Laptop GPU", "")
        cleaned = cleaned.replace("RTX", "RTX ").replace("  ", " ").strip()
        return cleaned or "待检测"


