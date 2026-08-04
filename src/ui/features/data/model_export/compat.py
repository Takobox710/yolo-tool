from __future__ import annotations

from pathlib import Path

from src.services.model_export import ModelExportConfig
from src.ui.features.data.model_export import config as config_helpers
from src.ui.features.data.model_export import runtime_actions
from src.ui.features.data.model_export import selection as selection_helpers
from src.ui.shared.workers import Worker


class ModelExportCompatibilityMixin:
    """Keep the historical page methods while delegating feature logic."""

    def choose_model(self, combo):
        selection_helpers.choose_model(self, combo)

    def refresh_model_choices(self):
        selection_helpers.refresh_model_choices(self)

    def _model_display_path(self, value: str | Path) -> str:
        return selection_helpers.model_display_path(self, value)

    def choose_calibration_data(self, edit):
        selection_helpers.choose_calibration_data(self, edit)

    def download_generic_calibration_pack(self):
        selection_helpers.download_generic_calibration_pack_for(self)

    def _calibration_pack_progress(self, message: str, value: int) -> None:
        selection_helpers.calibration_pack_progress(self, message, value)

    def _apply_calibration_pack_result(self, _kind: str, payload) -> None:
        selection_helpers.apply_calibration_pack_result(self, _kind, payload)

    def _clear_calibration_worker(self, worker: Worker) -> None:
        selection_helpers.clear_calibration_worker(self, worker)

    def collect_config(self) -> ModelExportConfig:
        return config_helpers.collect_config(self)

    def model_path_from_text(self, value: str) -> str:
        return config_helpers.model_path_from_text(self, value)

    def resolve_project_value(self, value: str) -> str:
        return config_helpers.resolve_project_value(self, value)

    def update_environment_status(self, *_args):
        self.update_option_visibility()

    def preview_export(self):
        runtime_actions.preview_export(self)

    def start_export(self):
        runtime_actions.start_export(self)

    def poll_export_queue(self):
        runtime_actions.poll_export_queue(self)

    def stop_export(self):
        runtime_actions.stop_export(self)

    def finish_export(self, exit_code: int):
        runtime_actions.finish_export(self, exit_code)

    def _set_running_state(self, running: bool):
        runtime_actions.set_running_state(self, running)

    def open_output_dir(self):
        runtime_actions.open_output_dir(self)

    def _runtime_capability(self, export_format: str, precision: str):
        return self._runtime_capability_for(
            export_format, self._current_model_kind(), precision
        )

    def _runtime_capability_for(
        self, export_format: str, model_kind: str, precision: str
    ):
        return runtime_actions.runtime_capability_for(
            self, export_format, model_kind, precision
        )


__all__ = ["ModelExportCompatibilityMixin"]
