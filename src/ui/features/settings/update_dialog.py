from __future__ import annotations

import webbrowser
from pathlib import Path
from threading import Event

from src.services.runtime.release_updates import (
    ReleaseCheckResult,
    download_release_assets,
    launch_installer,
    pause_installer,
    resume_installer,
)
from src.services.model_export import load_installed_extension
from src.shared.qt import (
    QDialog,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QMessageBox,
    QSizePolicy,
    Qt,
    QVBoxLayout,
)
from src.ui.shared.workers import Worker


class ReleaseUpdateDialog(QDialog):
    """Modern Release update panel for the settings page."""

    def __init__(self, parent, result: ReleaseCheckResult):
        super().__init__(parent)
        self.result = result
        self._worker: Worker | None = None
        self._pause_event = Event()
        self._installer_process = None
        self._installer_paused = False
        self._download_started = False
        self.setObjectName("releaseUpdateDialog")
        self.setWindowTitle("GitHub Release 更新")
        self.setModal(True)
        self.setMinimumSize(680, 610)
        self.resize(720, 660)
        self.setSizeGripEnabled(False)
        self.setStyleSheet(_DIALOG_STYLE)
        self._build_layout()

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("GitHub Release 更新")
        title.setObjectName("releaseDialogTitle")
        header.addWidget(title)
        header.addStretch(1)
        current = QLabel(f"当前版本 {self.result.current_version}")
        current.setObjectName("releaseDialogCurrent")
        header.addWidget(current)
        layout.addLayout(header)

        latest_row = _metric_row("最新版本", self.result.latest_version or "-")
        layout.addWidget(latest_row)

        notes_label = QLabel("主要更新")
        notes_label.setObjectName("releaseDialogSection")
        layout.addWidget(notes_label)
        self.notes = QPlainTextEdit()
        self.notes.setObjectName("releaseDialogNotes")
        self.notes.setReadOnly(True)
        self.notes.setPlainText(self.result.release_notes or "暂无发布说明。")
        self.notes.setMinimumHeight(190)
        self.notes.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self.notes, 1)

        if _has_any_environment_update(self.result):
            environment_notice = QFrame()
            environment_notice.setObjectName("releaseEnvironmentNotice")
            environment_layout = QVBoxLayout(environment_notice)
            environment_layout.setContentsMargins(12, 10, 12, 10)
            environment_layout.setSpacing(4)
            notice_title = QLabel("检测到环境包也有更新")
            notice_title.setObjectName("releaseEnvironmentTitle")
            notice_text = QLabel("可在下方勾选环境包，与程序安装包一起下载。")
            notice_text.setObjectName("releaseEnvironmentText")
            notice_text.setWordWrap(True)
            environment_layout.addWidget(notice_title)
            environment_layout.addWidget(notice_text)
            layout.addWidget(environment_notice)
        elif _has_optional_extra_environment(self.result):
            environment_notice = QFrame()
            environment_notice.setObjectName("releaseEnvironmentNotice")
            environment_layout = QVBoxLayout(environment_notice)
            environment_layout.setContentsMargins(12, 10, 12, 10)
            environment_layout.setSpacing(4)
            notice_title = QLabel("当前环境无附加包")
            notice_title.setObjectName("releaseEnvironmentTitle")
            notice_text = QLabel("可在本界面选择性下载安装附加环境包。")
            notice_text.setObjectName("releaseEnvironmentText")
            notice_text.setWordWrap(True)
            environment_layout.addWidget(notice_title)
            environment_layout.addWidget(notice_text)
            layout.addWidget(environment_notice)

        progress_panel = QFrame()
        progress_panel.setObjectName("releaseProgressPanel")
        progress_layout = QVBoxLayout(progress_panel)
        progress_layout.setContentsMargins(12, 10, 12, 10)
        progress_layout.setSpacing(8)
        progress_header = QHBoxLayout()
        progress_title = QLabel("更新进度")
        progress_title.setObjectName("releaseDialogSection")
        progress_header.addWidget(progress_title)
        progress_header.addStretch(1)
        self.progress_percent = QLabel("0%")
        self.progress_percent.setObjectName("releaseProgressPercent")
        progress_header.addWidget(self.progress_percent)
        progress_layout.addLayout(progress_header)
        options = QHBoxLayout()
        options.setSpacing(14)
        options_title = QLabel("下载内容")
        options_title.setObjectName("releaseDownloadOptionsTitle")
        options.addWidget(options_title)
        self.program_checkbox = QCheckBox("程序安装包")
        self.program_checkbox.setObjectName("releaseProgramCheckbox")
        self.program_checkbox.setChecked(bool(self.result.installer_asset_url))
        self.program_checkbox.setEnabled(bool(self.result.installer_asset_url))
        options.addWidget(self.program_checkbox)
        self.base_environment_checkbox = QCheckBox("基础环境包")
        self.base_environment_checkbox.setObjectName("releaseBaseEnvironmentCheckbox")
        self.extra_environment_checkbox = QCheckBox("附加环境包")
        self.extra_environment_checkbox.setObjectName("releaseExtraEnvironmentCheckbox")
        for checkbox, enabled, checked in (
            (
                self.base_environment_checkbox,
                bool(self.result.installer_asset_url)
                and _has_environment_asset(self.result, "baseenv"),
                bool(self.result.installer_asset_url)
                and _has_environment_update(self.result, "baseenv"),
            ),
            (
                self.extra_environment_checkbox,
                _has_environment_asset(self.result, "extraenv"),
                False,
            ),
        ):
            checkbox.setEnabled(enabled)
            checkbox.setChecked(checked)
            options.addWidget(checkbox)
        options.addStretch(1)
        progress_layout.addLayout(options)
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("releaseProgressBar")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        progress_layout.addWidget(self.progress_bar)
        self.progress_message = QLabel("安装包尚未下载。")
        self.progress_message.setObjectName("releaseProgressMessage")
        progress_layout.addWidget(self.progress_message)
        layout.addWidget(progress_panel)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.github_button = QPushButton("访问 GitHub 仓库")
        self.github_button.setObjectName("releaseGithubButton")
        self.github_button.setEnabled(bool(self.result.release_url))
        self.github_button.clicked.connect(self._open_github)
        buttons.addWidget(self.github_button)
        buttons.addStretch(1)
        self.download_button = QPushButton("下载并运行安装包")
        self.download_button.setObjectName("releaseDownloadButton")
        self.download_button.clicked.connect(self._start_download)
        self.pause_button = QPushButton("暂停")
        self.pause_button.setObjectName("releasePauseButton")
        self.pause_button.setEnabled(False)
        self.pause_button.clicked.connect(self._toggle_pause)
        for checkbox in (
            self.program_checkbox,
            self.base_environment_checkbox,
            self.extra_environment_checkbox,
        ):
            checkbox.stateChanged.connect(self._handle_selection_changed)
        self._sync_download_button()
        buttons.addWidget(self.download_button)
        buttons.addWidget(self.pause_button)
        close_button = QPushButton("关闭")
        close_button.setObjectName("releaseCloseButton")
        close_button.clicked.connect(self._request_close)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

    def _open_github(self) -> None:
        if self.result.release_url:
            webbrowser.open(self.result.release_url)

    def _start_download(self) -> None:
        if self._worker is not None:
            return
        if not self._confirm_download_selection():
            return
        assets = self._selected_assets()
        if not assets:
            self._set_progress_message("请至少勾选一个下载内容。")
            return
        self.download_button.setEnabled(False)
        self.github_button.setEnabled(False)
        self._set_option_enabled(False)
        self._download_started = True
        self._pause_event.clear()
        self._installer_process = None
        self._installer_paused = False
        self.pause_button.setText("暂停下载")
        self.pause_button.setEnabled(True)
        self.progress_bar.setValue(8)
        self._set_progress_message("正在准备下载…")
        worker = Worker(
            "release_assets_download",
            lambda report: download_release_assets(
                assets,
                progress=lambda name, index, count, downloaded, total: report(
                    f"正在下载{name}…",
                    _aggregate_download_percent(index, count, downloaded, total),
                ),
                pause_event=self._pause_event,
            ),
            accepts_progress=True,
        )
        self._worker = worker
        worker.progress.connect(self._apply_progress)
        worker.finished_with_payload.connect(self._apply_download_result)
        worker.finished.connect(lambda: self._clear_worker(worker))
        worker.start()

    def _apply_progress(self, message: str, value: int) -> None:
        if self._pause_event.is_set():
            return
        self.progress_bar.setValue(value)
        self.progress_percent.setText(f"{value}%")
        self._set_progress_message(message)

    def _apply_download_result(self, _kind: str, payload) -> None:
        if isinstance(payload, dict) and payload.get("error"):
            self._pause_event.clear()
            self._set_pause_button(False)
            self.progress_bar.setValue(0)
            self.progress_percent.setText("0%")
            self._set_progress_message(
                f"下载安装包失败：{payload['error']}", warning=True
            )
            self.download_button.setEnabled(True)
            self.github_button.setEnabled(bool(self.result.release_url))
            self._set_option_enabled(True)
            return
        paths = tuple(Path(str(path)) for path in (payload or ()))
        program_path = next(
            (path for path in paths if path.name == self.result.installer_asset_name),
            None,
        )
        installer_error = ""
        if self.program_checkbox.isChecked():
            if program_path is None:
                installer_error = "下载结果中没有找到程序安装包。"
            else:
                try:
                    self._installer_process = launch_installer(program_path)
                except Exception as exc:  # pragma: no cover - platform launcher
                    installer_error = str(exc) or "系统拒绝启动安装包。"
        extra_path = next(
            (
                path
                for path in paths
                if path.name.casefold().startswith("yolotool_extraenv_")
            ),
            None,
        )
        hot_install_started = False
        if (
            extra_path is not None
            and self.extra_environment_checkbox.isChecked()
            and not self.program_checkbox.isChecked()
        ):
            hot_install_started = self._hot_install_extra_environment(extra_path)
        self.progress_bar.setValue(100)
        self.progress_percent.setText("100%")
        self._pause_event.clear()
        self._set_pause_button(False)
        names = "、".join(path.name for path in paths)
        if installer_error:
            self._set_progress_message(
                f"已下载：{names}，但安装包启动失败：{installer_error}",
                warning=True,
            )
            self.download_button.setEnabled(True)
            self.github_button.setEnabled(bool(self.result.release_url))
            self._set_option_enabled(True)
        elif program_path is not None:
            self._set_progress_message(f"已下载 {names}，安装包已启动。")
            if self._installer_process is not None:
                self.pause_button.setText("暂停安装")
                self.pause_button.setEnabled(True)
        elif hot_install_started:
            self._set_progress_message(f"已下载：{names}，附加环境包正在热安装。")
        else:
            self._set_progress_message(f"已下载：{names}。")

    def _clear_worker(self, worker: Worker) -> None:
        if self._worker is worker:
            self._worker = None

    def _set_progress_message(self, message: str, *, warning: bool = False) -> None:
        self.progress_message.setText(message)
        self.progress_message.setProperty("warning", warning)
        style = self.progress_message.style()
        style.unpolish(self.progress_message)
        style.polish(self.progress_message)

    def _set_pause_button(self, enabled: bool) -> None:
        self.pause_button.setEnabled(enabled)
        if not enabled:
            self.pause_button.setText("暂停")

    def _toggle_pause(self) -> None:
        if self._worker is not None:
            if self._pause_event.is_set():
                self._pause_event.clear()
                self.pause_button.setText("暂停下载")
                self._set_progress_message("正在继续下载…")
            else:
                self._pause_event.set()
                self.pause_button.setText("继续下载")
                self._set_progress_message("下载已暂停。")
            return
        if self._installer_process is None:
            return
        try:
            if self._installer_paused:
                resume_installer(self._installer_process)
                self._installer_paused = False
                self.pause_button.setText("暂停安装")
                self._set_progress_message("安装器已继续运行。")
            else:
                pause_installer(self._installer_process)
                self._installer_paused = True
                self.pause_button.setText("继续安装")
                self._set_progress_message("安装器已暂停。")
        except Exception as exc:  # pragma: no cover - platform process state
            self._set_progress_message(f"无法控制安装器：{exc}", warning=True)
            self._set_pause_button(False)

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

    def _all_resources_selected(self) -> bool:
        return (
            self.program_checkbox.isChecked()
            and self.base_environment_checkbox.isChecked()
            and self.extra_environment_checkbox.isChecked()
        )

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

    def _only_extra_environment_selected(self) -> bool:
        return (
            self.extra_environment_checkbox.isChecked()
            and not self.program_checkbox.isChecked()
            and not self.base_environment_checkbox.isChecked()
        )

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

    @staticmethod
    def _installed_extra_environment():
        try:
            return load_installed_extension()
        except Exception:
            return None

    def _request_close(self) -> None:
        if self._worker is not None:
            self._set_progress_message("下载进行中，完成前无法关闭更新窗口。")
            return
        super().reject()

    def _handle_selection_changed(self) -> None:
        self._sync_download_button()

    def closeEvent(self, event):  # noqa: N802 - Qt API name
        if self._worker is not None:
            self._set_progress_message("下载进行中，完成前无法关闭更新窗口。")
            event.ignore()
            return
        super().closeEvent(event)

    def reject(self) -> None:
        self._request_close()


def _metric_row(label: str, value: str) -> QFrame:
    row = QFrame()
    row.setObjectName("releaseMetricRow")
    row_layout = QHBoxLayout(row)
    row_layout.setContentsMargins(0, 0, 0, 10)
    row_layout.setSpacing(14)
    label_widget = QLabel(label)
    label_widget.setObjectName("releaseMetricLabel")
    row_layout.addWidget(label_widget)
    value_widget = QLabel(value)
    value_widget.setObjectName("releaseMetricValue")
    row_layout.addWidget(value_widget)
    row_layout.addStretch(1)
    return row


def _download_percent(downloaded: int, total: int) -> int:
    if total <= 0:
        return 8
    return max(8, min(99, int(downloaded * 100 / total)))


def _aggregate_download_percent(
    index: int,
    count: int,
    downloaded: int,
    total: int,
) -> int:
    current = _download_percent(downloaded, total)
    return max(8, min(99, int((index * 100 + current) / max(1, count))))


def _find_environment_asset(
    result: ReleaseCheckResult,
    prefix: str,
) -> tuple[str, str] | None:
    for name, url in zip(result.environment_asset_names, result.environment_asset_urls):
        if name.casefold().startswith(f"yolotool_{prefix}_") and url:
            return name, url
    return None


def _has_environment_asset(result: ReleaseCheckResult, prefix: str) -> bool:
    return _find_environment_asset(result, prefix) is not None


def _has_environment_update(result: ReleaseCheckResult, prefix: str) -> bool:
    field = {
        "baseenv": "base_environment_update_available",
        "extraenv": "extra_environment_update_available",
    }.get(prefix)
    value = getattr(result, field, None) if field else None
    if value is None:
        return _has_environment_asset(result, prefix)
    return bool(value)


def _has_any_environment_update(result: ReleaseCheckResult) -> bool:
    return _has_environment_update(result, "baseenv") or _has_environment_update(
        result, "extraenv"
    )


def _has_optional_extra_environment(result: ReleaseCheckResult) -> bool:
    return (
        _has_environment_asset(result, "extraenv")
        and not _has_environment_update(result, "extraenv")
        and not str(result.installed_extra_environment_version or "").strip()
    )


_DIALOG_STYLE = """
QDialog#releaseUpdateDialog {
    background: #FFFFFF;
    color: #14233A;
    border: 1px solid #D9E3EC;
    border-radius: 12px;
}
QLabel#releaseDialogTitle {
    color: #222222;
    font-size: 20px;
    font-weight: 700;
}
QLabel#releaseDialogCurrent,
QLabel#releaseProgressMessage {
    color: #6D6D6D;
    font-size: 13px;
}
QLabel#releaseProgressMessage[warning="true"] {
    color: #D92D20;
    font-weight: 700;
}
QLabel#releaseMetricLabel {
    color: #6D6D6D;
    font-size: 15px;
    min-width: 120px;
}
QLabel#releaseMetricValue {
    color: #202020;
    font-size: 16px;
    font-weight: 700;
}
QFrame#releaseMetricRow {
    border-bottom: 1px solid #E5E5E5;
}
QLabel#releaseDialogSection {
    color: #202020;
    font-size: 15px;
    font-weight: 700;
}
QPlainTextEdit#releaseDialogNotes {
    background: #FFFFFF;
    color: #303030;
    border: 1px solid #D7D7D7;
    border-radius: 6px;
    padding: 10px;
    font-size: 14px;
}
QFrame#releaseProgressPanel {
    background: #FFFFFF;
    border: 1px solid #D9D9D9;
    border-radius: 8px;
}
QFrame#releaseEnvironmentNotice {
    background: #FFFFFF;
    border: 1px solid #D9D9D9;
    border-radius: 8px;
}
QLabel#releaseEnvironmentTitle {
    color: #202020;
    font-size: 14px;
    font-weight: 700;
}
QLabel#releaseEnvironmentText {
    color: #6D6D6D;
    font-size: 13px;
}
QLabel#releaseProgressPercent {
    color: #6D6D6D;
    font-size: 13px;
}
QLabel#releaseDownloadOptionsTitle {
    color: #6D6D6D;
    font-size: 13px;
}
QCheckBox {
    color: #303030;
    font-size: 13px;
}
QProgressBar#releaseProgressBar {
    background: #E5E5E5;
    border: 0;
    border-radius: 4px;
}
QProgressBar#releaseProgressBar::chunk {
    background: #1688F5;
    border-radius: 4px;
}
QPushButton {
    min-height: 34px;
    padding: 0 14px;
    border-radius: 6px;
    font-size: 14px;
}
QPushButton#releaseDownloadButton {
    background: #202020;
    color: #FFFFFF;
    border: 0;
}
QPushButton#releaseDownloadButton:hover {
    background: #000000;
}
QPushButton#releaseDownloadButton:disabled {
    background: #BEBEBE;
    color: #FFFFFF;
}
QPushButton#releaseGithubButton,
QPushButton#releasePauseButton,
QPushButton#releaseCloseButton {
    background: #F2F2F2;
    color: #202020;
    border: 1px solid #E0E0E0;
}
QPushButton#releaseGithubButton:hover,
QPushButton#releasePauseButton:hover,
QPushButton#releaseCloseButton:hover {
    background: #E8E8E8;
}
"""


__all__ = ["ReleaseUpdateDialog"]
