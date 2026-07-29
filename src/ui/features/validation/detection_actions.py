from __future__ import annotations

from pathlib import Path

from src.services.data_ops import relative_path_from_project
from src.services.validation import IMAGE_SUFFIXES, VIDEO_SUFFIXES
from src.shared.qt import QComboBox, QFileDialog, QEvent, QMediaPlayer, QStyle
from src.ui.features.validation.helpers import ResultNavigator, ValidationYamlPatch
from src.ui.features.validation.result_list import show_validation_result_list
from src.ui.features.validation.results import (
    handle_detection_result,
    show_cached_source_result as show_cached_validation_source_result,
    clear_validation_previews as clear_validation_preview_widgets,
    show_detection_payload as show_detection_result_payload,
    show_source_preview as show_validation_source_preview,
)
from src.ui.features.validation.runtime import (
    apply_detect_done,
    apply_detect_error,
    finish_dataset_validation_for_page,
    open_detection_save_dir,
    poll_validation_queue,
    recover_validation_state_if_process_exited,
    start_current_source_detection,
    start_dataset_validation,
    start_detection,
    start_single_detection,
    stop_detection,
)
from src.ui.features.validation.sources import (
    SINGLE_FILE_SOURCE_OPTIONS,
    SOURCE_SCOPE_OPTIONS,
)
from src.ui.features.validation.state import (
    append_active_log,
    clear_active_log,
    config,
    connect_validation_persistence,
    dataset_split_dir,
    dataset_yaml_root_for_page,
    detection_config_or_warn,
    folder_source_path_for_page,
    get_model_path,
    handle_data_path_changed,
    handle_video_progress,
    handle_source_input_changed,
    handle_source_scope_changed,
    persist_validation_integer,
    persist_validation_model,
    persist_validation_numeric,
    persist_validation_value,
    prepare_temporary_validation_yaml,
    refresh_model_choices,
    refresh_source_items,
    resolve_combo_path_text,
    restore_temporary_validation_yaml_if_needed,
    scope_target_path_for_page,
    single_file_config,
    update_source_mode,
    update_video_mode_controls,
    is_video_detection_mode,
    val_override_value_for_scope,
)


class ValidationDetectionActionsMixin:
    def on_show(self):
        self.refresh_model_choices(self.context.settings.validation.model_path)
        self._connect_validation_persistence()

    def refresh_model_choices(self, preferred_model: str | None = None):
        return refresh_model_choices(self, preferred_model)

    def _connect_validation_persistence(self):
        return connect_validation_persistence(self)

    def _persist_validation_model(self, _text: str):
        return persist_validation_model(self, _text)

    def _persist_validation_value(self, key: str, value):
        return persist_validation_value(self, key, value)

    def _handle_source_input_changed(self):
        return handle_source_input_changed(self)

    def _handle_data_path_changed(self):
        return handle_data_path_changed(self)

    def _handle_source_scope_changed(self, value: str):
        return handle_source_scope_changed(self, value)

    def _persist_validation_numeric(self, key: str, text: str):
        return persist_validation_numeric(self, key, text)

    def _persist_validation_integer(self, key: str, text: str):
        return persist_validation_integer(self, key, text)

    def _get_model_path(self) -> str:
        return get_model_path(self)

    def resolve_combo_path_text(self, text: str) -> str:
        return resolve_combo_path_text(self, text)

    def config(self):
        return config(self)

    def detection_config_or_warn(self) -> dict | None:
        return detection_config_or_warn(self)

    def single_file_config(self, path: Path, base_config: dict | None = None) -> dict:
        return single_file_config(self, path, base_config)

    def _dataset_yaml_root(self, payload: dict, data_path: Path) -> Path:
        return dataset_yaml_root_for_page(payload, data_path)

    def _val_override_value_for_scope(self, data_path: Path, scope: str) -> str:
        return val_override_value_for_scope(self, data_path, scope)

    def _prepare_temporary_validation_yaml(self, data_path: Path, scope: str) -> None:
        return prepare_temporary_validation_yaml(self, data_path, scope)

    def _restore_temporary_validation_yaml_if_needed(self) -> None:
        return restore_temporary_validation_yaml_if_needed(self)

    def clear_active_log(self):
        return clear_active_log(self)

    def append_active_log(self, text: str):
        return append_active_log(self, text)

    def start_detection(self):
        return start_detection(self)

    def start_dataset_validation(self):
        return start_dataset_validation(self)

    def start_current_source_detection(self):
        return start_current_source_detection(self)

    def start_single_detection(self, path: Path):
        return start_single_detection(self, path)

    def apply_detect_done(self, results):
        return apply_detect_done(self, results)

    def apply_detect_error(self, message):
        return apply_detect_error(self, message)

    def stop_detection(self):
        return stop_detection(self)

    def poll_validation_queue(self):
        return poll_validation_queue(self)

    def _recover_validation_state_if_process_exited(self):
        return recover_validation_state_if_process_exited(self)

    def _finish_dataset_validation(self, exit_code: int):
        return finish_dataset_validation_for_page(self, exit_code)

    def handle_result(self, payload):
        handle_detection_result(self, payload)

    def handle_video_progress(self, payload):
        return handle_video_progress(self, payload)

    def handle_video_completed(self, payload):
        source_path = payload.get("source_path")
        result_path = payload.get("result_path")
        if source_path and result_path:
            key = str(Path(source_path).resolve())
            self.video_result_by_source[key] = Path(result_path).resolve()
            if key == str(self.current_video_source_path):
                self.current_video_result_path = Path(result_path).resolve()
                self.video_playback.load_result(
                    self.current_video_result_path,
                    autoplay=False,
                )


