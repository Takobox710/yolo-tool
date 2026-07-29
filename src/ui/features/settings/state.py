"""Compatibility facade for settings page state domains."""

from __future__ import annotations

from src.services.runtime import application_version
from src.services.runtime.release_updates import ReleaseCheckResult, check_latest_release
from src.ui.features.settings.environment_state import (
    apply_env_data,
    auto_refresh,
    build_control_widgets,
    format_dependency_status,
    format_torch_status,
    load_env_payload,
    reset_defaults,
    toggle_custom_cmd,
    toggle_distribution_mode,
    toggle_help_icons,
    toggle_show_last_training_models,
)
from src.ui.features.settings.release_state import (
    append_program_log_entry,
    apply_release_check,
    open_release_update_dialog,
)


def on_show(page):
    if not page._auto_refresh_timer.isActive():
        page._auto_refresh_timer.start()
    for label in page.status_cards:
        page.set_status_card(label, "检测中...")
    page.log.setPlainText(page.program_log_text())
    page.context.run_background("env", lambda: load_env_payload(page))
    if not page.context.release_check_started:
        page.context.release_check_started = True
        page.context.run_background(
            "release_check",
            lambda: check_latest_release(),
            receiver=page,
        )


__all__ = [
    "ReleaseCheckResult",
    "append_program_log_entry",
    "apply_env_data",
    "apply_release_check",
    "auto_refresh",
    "build_control_widgets",
    "check_latest_release",
    "format_dependency_status",
    "format_torch_status",
    "load_env_payload",
    "on_show",
    "open_release_update_dialog",
    "reset_defaults",
    "toggle_custom_cmd",
    "toggle_distribution_mode",
    "toggle_help_icons",
    "toggle_show_last_training_models",
]
