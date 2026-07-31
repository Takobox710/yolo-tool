from __future__ import annotations

from src.shared.qt import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)
from src.services.runtime.variant import CPU_VARIANT, normalize_variant
from src.ui.features.settings.update_dialog_state import (
    has_environment_asset as _has_environment_asset,
    has_environment_update as _has_environment_update,
)


def metric_row(label: str, value: str) -> QFrame:
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


def build_release_update_layout(dialog) -> None:
    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(20, 18, 20, 18)
    layout.setSpacing(14)

    header = QHBoxLayout()
    title = QLabel("GitHub Release 更新")
    title.setObjectName("releaseDialogTitle")
    header.addWidget(title)
    header.addStretch(1)
    dialog.current_version_label = QLabel(
        f"当前版本 {dialog.result.current_version}"
    )
    current = dialog.current_version_label
    current.setObjectName("releaseDialogCurrent")
    header.addWidget(current)
    layout.addLayout(header)

    latest_row = metric_row("最新版本", dialog.result.latest_version or "-")
    dialog.latest_version_label = latest_row.findChild(
        QLabel, "releaseMetricValue"
    )
    layout.addWidget(latest_row)

    notes_label = QLabel("主要更新")
    notes_label.setObjectName("releaseDialogSection")
    layout.addWidget(notes_label)
    dialog.notes = QPlainTextEdit()
    dialog.notes.setObjectName("releaseDialogNotes")
    dialog.notes.setReadOnly(True)
    dialog.notes.setPlainText(dialog.result.release_notes or "暂无发布说明。")
    dialog.notes.setMinimumHeight(190)
    dialog.notes.setSizePolicy(
        QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
    )
    layout.addWidget(dialog.notes, 1)

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
    dialog.progress_percent = QLabel("0%")
    dialog.progress_percent.setObjectName("releaseProgressPercent")
    dialog.download_speed_label = QLabel("下载速度：0 B/s")
    dialog.download_speed_label.setObjectName("releaseDownloadSpeed")
    dialog.download_size_label = QLabel("已下载：0 B / --")
    dialog.download_size_label.setObjectName("releaseDownloadSize")
    progress_header.addWidget(dialog.download_speed_label)
    progress_header.addWidget(dialog.download_size_label)
    progress_header.addWidget(dialog.progress_percent)
    progress_layout.addLayout(progress_header)

    options = QHBoxLayout()
    options.setSpacing(14)
    options_title = QLabel("下载内容")
    options_title.setObjectName("releaseDownloadOptionsTitle")
    options.addWidget(options_title)
    dialog.program_checkbox = QCheckBox("程序安装包")
    dialog.program_checkbox.setObjectName("releaseProgramCheckbox")
    dialog.program_checkbox.setChecked(bool(dialog.result.installer_asset_url))
    dialog.program_checkbox.setEnabled(bool(dialog.result.installer_asset_url))
    options.addWidget(dialog.program_checkbox)
    dialog.base_environment_checkbox = QCheckBox("基础环境包")
    dialog.base_environment_checkbox.setObjectName("releaseBaseEnvironmentCheckbox")
    dialog.base_environment_checkbox.setVisible(
        normalize_variant(dialog.result.variant) != CPU_VARIANT
    )
    dialog.extra_environment_checkbox = QCheckBox("附加环境包")
    dialog.extra_environment_checkbox.setObjectName("releaseExtraEnvironmentCheckbox")
    dialog.extra_environment_checkbox.setVisible(
        normalize_variant(dialog.result.variant) != CPU_VARIANT
    )
    for checkbox, enabled, checked in (
        (
            dialog.base_environment_checkbox,
            normalize_variant(dialog.result.variant) != CPU_VARIANT
            and bool(dialog.result.installer_asset_url)
            and _has_environment_asset(dialog.result, "baseenv"),
            normalize_variant(dialog.result.variant) != CPU_VARIANT
            and bool(dialog.result.installer_asset_url)
            and _has_environment_update(dialog.result, "baseenv"),
        ),
        (
            dialog.extra_environment_checkbox,
            _has_environment_asset(dialog.result, "extraenv"),
            False,
        ),
    ):
        checkbox.setEnabled(enabled)
        checkbox.setChecked(checked)
        options.addWidget(checkbox)
    options.addStretch(1)
    progress_layout.addLayout(options)
    dialog.progress_bar = QProgressBar()
    dialog.progress_bar.setObjectName("releaseProgressBar")
    dialog.progress_bar.setRange(0, 100)
    dialog.progress_bar.setValue(0)
    dialog.progress_bar.setTextVisible(False)
    dialog.progress_bar.setFixedHeight(8)
    progress_layout.addWidget(dialog.progress_bar)
    dialog.progress_message = QLabel("安装包尚未下载。")
    dialog.progress_message.setObjectName("releaseProgressMessage")
    progress_layout.addWidget(dialog.progress_message)
    layout.addWidget(progress_panel)
    dialog._main_layout = layout
    dialog._progress_panel = progress_panel
    dialog.environment_notice = None
    dialog._sync_environment_notice()

    buttons = QHBoxLayout()
    buttons.setSpacing(8)
    dialog.github_button = QPushButton("访问 GitHub 仓库")
    dialog.github_button.setObjectName("releaseGithubButton")
    dialog.github_button.setEnabled(bool(dialog.result.release_url))
    dialog.github_button.clicked.connect(dialog._open_github)
    buttons.addWidget(dialog.github_button)
    dialog.refresh_button = QPushButton("检测更新")
    dialog.refresh_button.setObjectName("releaseRefreshButton")
    dialog.refresh_button.clicked.connect(dialog._request_release_check)
    buttons.addWidget(dialog.refresh_button)
    buttons.addStretch(1)
    dialog.download_button = QPushButton("下载并运行安装包")
    dialog.download_button.setObjectName("releaseDownloadButton")
    dialog.download_button.clicked.connect(dialog._start_download)
    dialog.pause_button = QPushButton("暂停")
    dialog.pause_button.setObjectName("releasePauseButton")
    dialog.pause_button.setEnabled(False)
    dialog.pause_button.clicked.connect(dialog._toggle_pause)
    dialog.stop_button = QPushButton("停止")
    dialog.stop_button.setObjectName("releaseStopButton")
    dialog.stop_button.setEnabled(False)
    dialog.stop_button.clicked.connect(dialog._stop_download)
    for checkbox in (
        dialog.program_checkbox,
        dialog.base_environment_checkbox,
        dialog.extra_environment_checkbox,
    ):
        checkbox.stateChanged.connect(dialog._handle_selection_changed)
    dialog._sync_download_button()
    dialog._sync_release_check_button()
    buttons.addWidget(dialog.download_button)
    buttons.addWidget(dialog.pause_button)
    buttons.addWidget(dialog.stop_button)
    close_button = QPushButton("关闭")
    close_button.setObjectName("releaseCloseButton")
    close_button.clicked.connect(dialog._request_close)
    buttons.addWidget(close_button)
    layout.addLayout(buttons)


__all__ = ["build_release_update_layout", "metric_row"]
