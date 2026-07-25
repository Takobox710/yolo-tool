from __future__ import annotations

from pathlib import Path
from typing import Any

from src.services.data_ops import display_project_path, resolve_project_path
from src.services.settings import settings_to_dict
from src.ui.shared.forms import FormPageMixin
from src.ui.shared.context import WorkbenchContext
from src.ui.helpers import history_number_sort_key, history_time_sort_key
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
    def __init__(self, context):
        super().__init__()
        self.context = context if isinstance(context, WorkbenchContext) else _legacy_context(context)

    def project_root(self) -> Path:
        return Path(self.context.settings.project.root)

    def save_settings(self):
        return self.context.save_settings(source=self)

    def set_status_text(self, text: str) -> None:
        self.append_program_log(text)

    def update_setting(self, *keys: str, value: Any):
        if not keys:
            return
        target = self.context.settings
        for key in keys[:-1]:
            target = getattr(target, key)
        setattr(target, keys[-1], value)
        self.save_settings()

    def on_setting_changed(self, keys: tuple[str, ...], value: Any) -> None:
        """Hook for controls that mirror shared project settings."""
        return None

    def display_path(self, path: str | Path) -> str:
        return display_project_path(str(path), self.project_root())

    def resolve_path_text(self, edit: QLineEdit) -> str:
        return resolve_project_path(edit.text(), self.project_root())

    def path_from_edit(self, edit: QLineEdit) -> Path:
        return Path(self.resolve_path_text(edit))

    def append_program_log(self, text: str, *, level: str | None = None) -> None:
        self.context.append_program_log(text, level=level or self.infer_log_level(text))

    def program_log_text(self) -> str:
        return self.context.program_log_text()

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
            self.context.settings.features.show_help_icons
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


def _legacy_context(host) -> WorkbenchContext:
    """Temporary adapter for older third-party page constructors."""
    settings = host.settings
    service = host.settings_service
    original_save = service.save

    def save_legacy(value):
        try:
            original_save(value)
        except (TypeError, AttributeError):
            original_save(settings_to_dict(value))

    host_background = getattr(host, "run_background", None)
    run_background = (
        (lambda kind, fn, receiver=None: host_background(kind, fn))
        if callable(host_background)
        else None
    )

    def refresh_validation_models() -> None:
        for page in getattr(host, "pages", {}).values():
            target = getattr(page, "inner_page", page)
            hook = getattr(target, "refresh_model_choices", None)
            if callable(hook):
                hook()

    def refresh_help_icons() -> None:
        for page in getattr(host, "pages", {}).values():
            target = getattr(page, "inner_page", page)
            hook = getattr(target, "refresh_help_icon_visibility", None)
            if callable(hook):
                hook()

    status = getattr(host, "status", None)
    append_log = (
        (lambda text, **_kwargs: status.setText(text))
        if status is not None and callable(getattr(status, "setText", None))
        else None
    )
    context = WorkbenchContext(
        service,
        type("LoadResult", (), {"settings": settings, "migrated": False, "issues": ()})(),
        run_background=run_background,
        append_log=append_log,
        program_log=lambda: "等待程序日志...",
        refresh_help_icons=refresh_help_icons,
        refresh_validation_models=refresh_validation_models,
    )
    context.settings_service.save = save_legacy
    return context
