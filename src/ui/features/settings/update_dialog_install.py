from __future__ import annotations

from pathlib import Path

from src.services.model_export import load_installed_extension
from src.shared.theme import build_release_dialog_style
from src.ui.shared.theme import current_theme_mode


class ReleaseUpdateInstallMixin:

    def _request_close(self) -> None:
        if self._worker is not None:
            self.hide()
            return
        super().reject()


    def _hot_install_extra_environment(self, path: Path) -> bool:
        owner = self.parentWidget()
        install = getattr(owner, "install_model_export_package", None)
        if callable(install):
            install(path)
            return True
        self._set_progress_message(
            f"附加环境包已下载：{path.name}，请在系统设置中导入并安装。"
        )
        return False


    def closeEvent(self, event):  # noqa: N802 - Qt API name
        if self._worker is not None:
            self.hide()
            event.accept()
            return
        super().closeEvent(event)


    def reject(self) -> None:
        self._request_close()


def _installed_extra_environment():
    try:
        return load_installed_extension()
    except Exception:
        return None


def apply_release_dialog_style(dialog) -> None:
    dialog.setStyleSheet(build_release_dialog_style(current_theme_mode()))


__all__ = ["ReleaseUpdateInstallMixin", "apply_release_dialog_style"]
