from __future__ import annotations

from src.ui.features.settings.constants import STATUS_CARD_LABELS
from src.ui.features.settings.layout import build_settings_layout
from src.ui.features.settings.state import (
    append_program_log_entry,
    apply_env_data,
    auto_refresh,
    build_control_widgets,
    load_env_payload,
    on_show,
    reset_defaults,
    toggle_custom_cmd,
    toggle_distribution_mode,
    toggle_help_icons,
    toggle_show_last_training_models,
)
from src.ui.shared.page_base import BasePage
from src.ui.shared.model_export_package import ModelExportPackageDropMixin
from src.services.runtime import invalidate_cache
from src.shared.qt import QTimer


class SettingsPage(ModelExportPackageDropMixin, BasePage):
    def __init__(self, context):
        super().__init__(context)
        self.setup_model_export_package_drop()
        self._refresh_count = 0
        build_settings_layout(self)
        self.finalize_model_export_package_drop()
        self.distribution_mode_check.setChecked(
            self.context.settings.features.distribution_multi_class_mode
        )

        self._auto_refresh_timer = QTimer(self)
        self._auto_refresh_timer.timeout.connect(self._auto_refresh)
        self._auto_refresh_timer.setInterval(500)

    def _build_control_widgets(self):
        return build_control_widgets(self)

    def _toggle_custom_cmd(self, state):
        return toggle_custom_cmd(self, state)

    def _toggle_distribution_mode(self, state):
        return toggle_distribution_mode(self, state)

    def _toggle_help_icons(self, state):
        return toggle_help_icons(self, state)

    def _toggle_show_last_training_models(self, state):
        return toggle_show_last_training_models(self, state)

    def _reset_defaults(self):
        return reset_defaults(self)

    def _auto_refresh(self):
        return auto_refresh(self)

    def on_show(self):
        return on_show(self)

    def on_hide(self):
        self._auto_refresh_timer.stop()

    def _load_env_payload(self):
        return load_env_payload(self)

    def set_status_card(self, label: str, value: str):
        self.status_cards[label].setText(value)

    def apply_env(self, payload):
        self._apply_env_data(payload)

    def apply_env_auto(self, payload):
        self._apply_env_data(payload)

    def _apply_env_data(self, payload):
        return apply_env_data(self, payload)

    def append_program_log_entry(self, entry: str) -> None:
        return append_program_log_entry(self, entry)

    def model_export_package_installing_changed(self, installing: bool) -> None:
        if installing:
            self.append_program_log_entry("正在校验并安装模型转换附加包...")

    def model_export_package_install_progress(self, message: str, value: int) -> None:
        self.append_program_log_entry(f"{message}（{value}%）")

    def model_export_package_installed(self, installed) -> None:
        invalidate_cache("dependency_versions")
        self.append_program_log_entry(
            f"已启用模型转换附加环境 {installed.version}。"
        )
        self.on_show()
