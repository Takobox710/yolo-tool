from __future__ import annotations

import webbrowser
from pathlib import Path
from threading import Event

from src.services.runtime.release_updates import (
    ReleaseCheckResult,
    check_latest_release,
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
    QTimer,
    QVBoxLayout,
)
from src.ui.features.settings.update_dialog_state import (
    apply_download_detail as _apply_download_detail,
    apply_release_check_result as _apply_release_check_result,
    build_download_progress_reporter as _build_download_progress_reporter,
    download_percent as _download_percent,
    download_weights as _download_weights,
    aggregate_download_percent as _aggregate_download_percent,
    find_environment_asset as _find_environment_asset,
    has_any_environment_update as _has_any_environment_update,
    has_environment_asset as _has_environment_asset,
    has_environment_update as _has_environment_update,
    has_optional_extra_environment as _has_optional_extra_environment,
    release_check_is_active as _release_check_is_active,
    sync_environment_notice as _sync_environment_notice,
    update_download_speed as _update_download_speed,
)
from src.ui.features.settings.update_dialog_layout import (
    build_release_update_layout,
    metric_row as _metric_row,
)
from src.ui.features.settings.update_dialog_download import ReleaseUpdateDownloadMixin
from src.ui.features.settings.update_dialog_install import (
    ReleaseUpdateInstallMixin,
    _DIALOG_STYLE,
)
from src.ui.features.settings.update_dialog_selection import ReleaseUpdateSelectionMixin
from src.ui.shared.workers import Worker


class ReleaseUpdateDialog(
    ReleaseUpdateDownloadMixin,
    ReleaseUpdateSelectionMixin,
    ReleaseUpdateInstallMixin,
    QDialog,
):
    """Modern Release update panel for the settings page."""

    def __init__(self, parent, result: ReleaseCheckResult):
        super().__init__(parent)
        self.result = result
        self._worker: Worker | None = None
        self._pause_event = Event()
        self._stop_event = Event()
        self._installer_process = None
        self._installer_paused = False
        self._download_started = False
        self._download_running = False
        self._latest_downloaded = 0
        self._speed_baseline_downloaded = 0
        self._release_check_in_progress = _release_check_is_active(parent)
        self._download_speed_timer = QTimer(self)
        self._download_speed_timer.setInterval(1000)
        self._download_speed_timer.timeout.connect(self._update_download_speed)
        self.setObjectName("releaseUpdateDialog")
        self.setWindowTitle("GitHub Release 更新")
        self.setModal(True)
        self.setMinimumSize(680, 610)
        self.resize(720, 660)
        self.setSizeGripEnabled(False)
        self.setStyleSheet(_DIALOG_STYLE)
        self._build_layout()

    def _build_layout(self) -> None:
        build_release_update_layout(self)

    def _open_github(self) -> None:
        if self.result.release_url:
            webbrowser.open(self.result.release_url)

    def apply_release_check_result(self, result: ReleaseCheckResult) -> None:
        _apply_release_check_result(self, result)

    def _sync_environment_notice(self) -> None:
        _sync_environment_notice(self)

    @staticmethod
    def _installed_extra_environment():
        try:
            return load_installed_extension()
        except Exception:
            return None
