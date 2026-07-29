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


class ValidationResultActionsMixin:
    def load_video_source(self, path: Path | str | None) -> None:
        if not path:
            return
        resolved = Path(path).resolve()
        self.current_video_source_path = resolved
        self.current_video_result_path = self.video_result_by_source.get(str(resolved))
        self.video_playback.load_source(resolved, autoplay=False)
        if self.current_video_result_path:
            self.video_playback.load_result(
                self.current_video_result_path,
                autoplay=False,
            )

    def stop_video_playback(self) -> None:
        self.video_playback.stop()

    def previous_video(self) -> None:
        self.refresh_source_items()
        if not self.source_items:
            return
        self.source_index = (self.source_index - 1) % len(self.source_items)
        self.load_video_source(self.source_items[self.source_index])

    def next_video(self) -> None:
        self.refresh_source_items()
        if not self.source_items:
            return
        self.source_index = (self.source_index + 1) % len(self.source_items)
        self.load_video_source(self.source_items[self.source_index])

    def show_detection_payload(self, payload):
        show_detection_result_payload(self, payload)

    def show_source_preview(self, path: Path):
        return show_validation_source_preview(self, path)

    def first_result(self):
        if not self.detection_started_for_source and self._navigate_source_preview("first"):
            return
        self.result_navigator.show_first()

    def last_result(self):
        if not self.detection_started_for_source and self._navigate_source_preview("last"):
            return
        self.result_navigator.show_last()

    def prev_result(self):
        if not self.detection_started_for_source and self._navigate_source_preview("previous"):
            return
        self.result_navigator.show_previous()

    def next_result(self):
        if not self.detection_started_for_source and self._navigate_source_preview("next"):
            return
        self.result_navigator.show_next()

    def _navigate_source_preview(self, action: str) -> bool:
        self.refresh_source_items()
        if not self.source_items:
            return False
        if action == "first":
            index = 0
        elif action == "last":
            index = len(self.source_items) - 1
        elif action == "previous":
            index = (self.source_index - 1) % len(self.source_items)
        else:
            index = (self.source_index + 1) % len(self.source_items)
        self.source_index = index
        self.show_source_preview(self.source_items[index])
        return True

    def show_source_index(self, index: int):
        self.refresh_source_items()
        if not self.source_items:
            return
        self.source_index = index % len(self.source_items)

    def show_cached_source_result(self, path: Path) -> bool:
        if self.is_video_detection_mode():
            self.load_video_source(path)
            result_path = self.video_result_by_source.get(str(Path(path).resolve()))
            if result_path:
                self.current_video_result_path = result_path
                self.video_playback.load_result(result_path, autoplay=False)
                return True
            return False
        if not self.detection_started_for_source:
            self.show_source_preview(path)
            return True
        return show_cached_validation_source_result(self, path)

    def show_result_list(self):
        self.refresh_source_items()
        show_validation_result_list(
            parent=self,
            source_items=self.source_items,
            source_index=self.source_index,
            set_source_index=lambda index: setattr(self, "source_index", index),
            show_cached_source_result=self.show_cached_source_result,
        )

    def open_detection_save_dir(self):
        return open_detection_save_dir(self)

