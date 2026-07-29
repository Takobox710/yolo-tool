from __future__ import annotations

from src.services.model_export import load_installed_extension
from src.shared.qt import QMessageBox
from src.ui.features.settings.update_dialog_state import (
    find_environment_asset as _find_environment_asset,
    has_any_environment_update as _has_any_environment_update,
    has_environment_asset as _has_environment_asset,
    has_environment_update as _has_environment_update,
)


class ReleaseUpdateSelectionMixin:

    def _handle_selection_changed(self) -> None:
        self._sync_download_button()


    def _selected_assets(self) -> tuple[tuple[str, str], ...]:
        assets: list[tuple[str, str]] = []
        if self.program_checkbox.isChecked() and self.result.installer_asset_url:
            assets.append((self.result.installer_asset_name, self.result.installer_asset_url))
        for checkbox, prefix in (
            (self.base_environment_checkbox, "baseenv"),
            (self.extra_environment_checkbox, "extraenv"),
        ):
            if checkbox.isChecked():
                asset = _find_environment_asset(self.result, prefix)
                if asset:
                    assets.append(asset)
        return tuple(assets)


    def _all_resources_selected(self) -> bool:
        return (
            self.program_checkbox.isChecked()
            and self.base_environment_checkbox.isChecked()
            and self.extra_environment_checkbox.isChecked()
        )


    def _only_extra_environment_selected(self) -> bool:
        return (
            self.extra_environment_checkbox.isChecked()
            and not self.program_checkbox.isChecked()
            and not self.base_environment_checkbox.isChecked()
        )


    def _sync_pre_download_message(self) -> None:
        if self._download_started:
            return
        if self._all_resources_selected():
            base_reinstall = not _has_environment_update(self.result, "baseenv")
            extra_replace = self._installed_extra_environment() is not None
            if base_reinstall and extra_replace:
                message = "基础环境包版本与本机一致，下载将重装基础环境包；附加包已安装，下载后将替换。"
                warning = True
            elif base_reinstall:
                message = "基础环境包版本与本机一致，下载将重装基础环境包；附加环境包下载完成后会自动安装。"
                warning = True
            elif extra_replace:
                message = "基础环境包将与程序安装包一起下载；附加包已安装，下载后将替换。"
                warning = True
            else:
                message = "程序安装包和基础环境包将同时下载；附加环境包下载完成后会自动安装。"
                warning = False
        elif self.base_environment_checkbox.isChecked() and not self.program_checkbox.isChecked():
            message = "仅有基础环境包没有程序无法安装，请勾选程序安装包。"
            warning = True
        elif self.base_environment_checkbox.isChecked():
            if _has_environment_update(self.result, "baseenv"):
                message = "基础环境包将与程序安装包一起下载。"
                warning = False
            else:
                message = "当前基础环境包版本与本机一致，无需下载；继续下载将重装一次基础环境包。"
                warning = True
        elif self._only_extra_environment_selected():
            if self._installed_extra_environment() is not None:
                message = "已经安装附加包，当前附加包为最新版本，下载后将替换。"
                warning = True
            else:
                message = "附加环境包下载完成后会在程序内自动安装。"
                warning = False
        elif self.program_checkbox.isChecked() and self.extra_environment_checkbox.isChecked():
            if self._installed_extra_environment() is not None:
                message = "已经安装附加包，下载后将替换；程序安装包将同时下载并运行。"
                warning = True
            else:
                message = "附加环境包下载完成后会在程序内自动安装；程序安装包将同时下载并运行。"
                warning = False
        elif self.program_checkbox.isChecked() and _has_any_environment_update(self.result):
            if self.result.update_available:
                message = "当前 Release 同时提供环境包，仅更新程序可能导致部分功能无法使用，点击下载时会确认。"
                warning = True
            else:
                message = "请勾选基础环境包，当前基础环境为旧版本，需下载并重装。"
                warning = True
        elif self.program_checkbox.isChecked():
            if self.result.update_available:
                message = "检测到最新版本，点击按钮即可更新。"
            else:
                message = "当前已是最新版本，无需更新。"
            warning = False
        else:
            message = "安装包尚未下载。"
            warning = False
        self._set_progress_message(message, warning=warning)

    def _confirm_extra_environment_replacement(self) -> bool:
        installed = self._installed_extra_environment()
        if installed is None:
            return True
        answer = QMessageBox.question(
            self,
            "重新下载附加包",
            "已经安装附加包，当前附加包为最新版本，是否重新下载并替换？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes


    def _confirm_all_resources(self) -> bool:
        base_reinstall = not _has_environment_update(self.result, "baseenv")
        extra_replace = self._installed_extra_environment() is not None
        if not base_reinstall and not extra_replace:
            return True
        details = []
        if base_reinstall:
            details.append("基础环境包版本与本机一致，继续下载将重装一次基础环境包")
        if extra_replace:
            details.append("附加环境包已安装，继续下载将替换现有附加环境包")
        answer = QMessageBox.warning(
            self,
            "确认重新安装环境包",
            "；".join(details) + "。\n仍要继续下载并运行安装包吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes


    def _confirm_download_selection(self) -> bool:
        if self.base_environment_checkbox.isChecked() and not self.program_checkbox.isChecked():
            QMessageBox.warning(
                self,
                "无法单独下载基础环境包",
                "仅有基础环境包没有程序无法安装，请勾选程序安装包。",
            )
            return False
        if self._all_resources_selected():
            return self._confirm_all_resources()
        if (
            self.program_checkbox.isChecked()
            and self.base_environment_checkbox.isChecked()
            and not _has_environment_update(self.result, "baseenv")
        ):
            answer = QMessageBox.warning(
                self,
                "基础环境包无需更新",
                "当前基础环境包版本与本机一致，环境包无需更新；继续下载将重装一次基础环境包。\n"
                "仍要继续吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            return answer == QMessageBox.StandardButton.Yes
        if (
            self.program_checkbox.isChecked()
            and self.extra_environment_checkbox.isChecked()
            and self._installed_extra_environment() is not None
        ):
            return self._confirm_extra_environment_replacement()
        if not self.program_checkbox.isChecked():
            if self._only_extra_environment_selected():
                return self._confirm_extra_environment_replacement()
            return True
        if self.base_environment_checkbox.isChecked() or self.extra_environment_checkbox.isChecked():
            return True
        if _has_any_environment_update(self.result):
            if not self.result.update_available:
                answer = QMessageBox.warning(
                    self,
                    "基础环境包需要更新",
                    "请勾选基础环境包，当前基础环境为旧版本，需下载并重装。\n"
                    "仍要只下载程序安装包吗？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                return answer == QMessageBox.StandardButton.Yes
            answer = QMessageBox.warning(
                self,
                "环境包未选择",
                "程序和环境包都需要更新，但当前只勾选了程序安装包。\n"
                "更新后的程序可能有部分功能无法使用，仍要继续吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            return answer == QMessageBox.StandardButton.Yes
        if self.result.update_available:
            return True
        answer = QMessageBox.question(
            self,
            "当前已是最新版本",
            "当前已是最新版本，无需更新，是否仍要下载并运行安装包？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes


    def _sync_download_button(self) -> None:
        if self.program_checkbox.isChecked():
            button_text = "下载并运行安装包"
        elif self._only_extra_environment_selected():
            button_text = "下载并安装所选资源"
        else:
            button_text = "下载所选资源"
        self.download_button.setText(button_text)
        self.download_button.setEnabled(
            self._worker is None and bool(self._selected_assets())
        )
        self._sync_pre_download_message()


    def _set_option_enabled(self, enabled: bool) -> None:
        self.program_checkbox.setEnabled(
            enabled and bool(self.result.installer_asset_url)
        )
        self.base_environment_checkbox.setEnabled(
            enabled
            and bool(self.result.installer_asset_url)
            and _has_environment_asset(self.result, "baseenv")
        )
        self.extra_environment_checkbox.setEnabled(
            enabled and _has_environment_asset(self.result, "extraenv")
        )


__all__ = ['ReleaseUpdateSelectionMixin']
