from __future__ import annotations

from pathlib import Path

from src.services.model_export import load_installed_extension


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
QLabel#releaseProgressPercent,
QLabel#releaseDownloadSpeed,
QLabel#releaseDownloadSize {
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
QPushButton#releaseRefreshButton,
QPushButton#releasePauseButton,
QPushButton#releaseStopButton,
QPushButton#releaseCloseButton {
    background: #F2F2F2;
    color: #202020;
    border: 1px solid #E0E0E0;
}
QPushButton#releaseGithubButton:hover,
QPushButton#releaseRefreshButton:hover,
QPushButton#releasePauseButton:hover,
QPushButton#releaseStopButton:hover,
QPushButton#releaseCloseButton:hover {
    background: #E8E8E8;
}
"""


__all__ = ['ReleaseUpdateInstallMixin']
