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


class ValidationPageActionsMixin:
    def _build_result_navigator(self):
        self.validation_yaml_patch = ValidationYamlPatch()
        self.result_navigator = ResultNavigator(
            lambda: self.detect_results,
            lambda: self.detect_index,
            lambda index: setattr(self, "detect_index", index),
            lambda selected: setattr(self, "user_selected_result", selected),
            self.show_detection_payload,
        )

    def update_source_mode(self, value):
        return update_source_mode(self, value)

    def clear_validation_previews(self):
        return clear_validation_preview_widgets(self)

    def is_video_detection_mode(self) -> bool:
        return is_video_detection_mode(self)

    def update_video_mode_controls(self) -> None:
        return update_video_mode_controls(self)

    def toggle_video_playback(self, enabled: bool) -> None:
        if not self.is_video_detection_mode():
            self._set_video_playback_button(False)
            return
        if enabled:
            self.video_playback.play_pair()
            self._set_video_playback_button(True)
        else:
            self.video_playback.pause_pair()
            self._set_video_playback_button(False)

    def _set_video_playback_button(self, playing: bool) -> None:
        self.video_play_btn.blockSignals(True)
        self.video_play_btn.setChecked(playing)
        self.video_play_btn.blockSignals(False)
        icon = (
            QStyle.StandardPixmap.SP_MediaPause
            if playing
            else QStyle.StandardPixmap.SP_MediaPlay
        )
        self.video_play_btn.setIcon(self.style().standardIcon(icon))
        self.video_play_btn.setToolTip("暂停视频" if playing else "播放视频")

    def handle_video_playback_state(self, state) -> None:
        self._set_video_playback_button(
            state == QMediaPlayer.PlaybackState.PlayingState
        )

    def handle_video_media_status(self, status) -> None:
        if status != QMediaPlayer.MediaStatus.EndOfMedia:
            return
        self.video_playback.pause_pair()
        self.video_progress.setValue(self.video_progress.maximum())
        self._set_video_playback_button(False)

    @staticmethod
    def _drop_media_path(event) -> Path | None:
        mime_data = event.mimeData()
        if not mime_data.hasUrls():
            return None
        for url in mime_data.urls():
            local_path = url.toLocalFile()
            if not local_path:
                continue
            path = Path(local_path)
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES | VIDEO_SUFFIXES:
                return path.resolve()
        return None

    def dragEnterEvent(self, event):  # noqa: N802 - Qt API name
        if self._drop_media_path(event) is not None:
            event.acceptProposedAction()
            return
        event.ignore()

    def _apply_dropped_media(self, path: Path) -> None:
        mode = "视频检测" if path.suffix.lower() in VIDEO_SUFFIXES else "图片检测"
        self.mode_combo.setCurrentText(mode)
        self.source_combo.setCurrentText(
            relative_path_from_project(str(path), self.project_root())
        )
        self._persist_validation_value("source_mode", mode)
        self._persist_validation_value("source_path", str(path))
        self._persist_validation_value(
            "source_selection",
            "单个视频" if mode == "视频检测" else "单张图片",
        )
        self.refresh_source_items()
        self.update_video_mode_controls()

    def dropEvent(self, event):  # noqa: N802 - Qt API name
        path = self._drop_media_path(event)
        if path is None:
            event.ignore()
            return
        self._apply_dropped_media(path)
        event.acceptProposedAction()

    def eventFilter(self, watched, event):  # noqa: N802 - Qt API name
        if event.type() in {
            QEvent.Type.DragEnter,
            QEvent.Type.DragMove,
            QEvent.Type.Drop,
        }:
            path = self._drop_media_path(event)
            if path is not None:
                if event.type() == QEvent.Type.Drop:
                    self._apply_dropped_media(path)
                event.acceptProposedAction()
                return True
        return super().eventFilter(watched, event)

    def is_val_mode(self, value: str | None = None) -> bool:
        return str(value or self.mode_combo.currentText()).strip() == "数据集验证"

    def _configure_source_combo(self, values: list[str], current_text: str, placeholder: str) -> None:
        self.source_combo.blockSignals(True)
        self.source_combo.clear()
        self.source_combo.addItems(values)
        self.source_combo.setCurrentText(str(current_text or ""))
        line_edit = self.source_combo.lineEdit()
        if line_edit is not None:
            line_edit.setPlaceholderText(placeholder)
        self.source_combo.blockSignals(False)

    def set_result_navigation_enabled(self, enabled: bool):
        for button in self.result_nav_buttons:
            button.setEnabled(enabled)

    def update_detection_button_text(self):
        self.start_det_btn.setText("开始检测")
        self.stop_det_btn.setText("停止")

    def choose_detection_source(self, combo: QComboBox):
        current_text = combo.currentText().strip()
        validation = self.app.settings.get("validation", {})
        saved_selection = validation.get("source_selection", "")
        current = (
            validation.get("source_path")
            if saved_selection in SINGLE_FILE_SOURCE_OPTIONS
            else (
                self.resolve_combo_path_text(current_text)
                if current_text
                and current_text not in SOURCE_SCOPE_OPTIONS
                and current_text not in {"单张图片", "批量视频", "单个视频"}
                else str(self.project_root())
            )
        )
        mode = self.mode_combo.currentText()
        is_single = (
            current_text in SINGLE_FILE_SOURCE_OPTIONS
            or saved_selection in SINGLE_FILE_SOURCE_OPTIONS
        )
        if is_single:
            suffixes = " ".join(
                f"*{suffix}"
                for suffix in sorted(
                    VIDEO_SUFFIXES if mode == "视频检测" else IMAGE_SUFFIXES
                )
            )
            path, _ = QFileDialog.getOpenFileName(
                self,
                "选择视频文件" if mode == "视频检测" else "选择图片文件",
                current or str(self.project_root()),
                f"支持的文件 ({suffixes});;所有文件 (*)",
            )
        else:
            path = QFileDialog.getExistingDirectory(
                self,
                "选择视频文件夹" if mode == "视频检测" else "选择图片文件夹",
                current or str(self.project_root()),
            )
        if not path:
            return
        selected = Path(path).resolve()
        if is_single:
            if not selected.is_file():
                return
            selected_option = "单个视频" if mode == "视频检测" else "单张图片"
        else:
            if not selected.is_dir():
                return
            selected_option = "批量视频" if mode == "视频检测" else ""
        combo.setCurrentText(relative_path_from_project(str(selected), self.project_root()))
        self._persist_validation_value("source_path", str(selected))
        self._persist_validation_value("source_selection", selected_option)
        self.refresh_source_items()
        self.update_video_mode_controls()

    def choose_validation_source(self, combo: QComboBox):
        current_text = combo.currentText().strip()
        current = (
            self.resolve_combo_path_text(current_text)
            if current_text and current_text not in SOURCE_SCOPE_OPTIONS
            else str(self.project_root())
        )
        path = QFileDialog.getExistingDirectory(
            self,
            "选择验证源文件夹",
            current,
        )
        if not path:
            return
        selected = Path(path).resolve()
        if not selected.is_dir():
            return
        display_path = relative_path_from_project(str(selected), self.project_root())
        combo.setCurrentText(display_path)
        self._persist_validation_value("source_scope", display_path)
        self.refresh_source_items()

    def choose_dataset_yaml(self, edit):
        current = self.resolve_path_text(edit) if edit.text() else str(self.project_root())
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择数据集 YAML",
            current,
            "YAML 文件 (*.yaml *.yml);;所有文件 (*)",
        )
        if path:
            edit.setText(self.display_path(path))

    def choose_output_dir(self, edit):
        self.choose_dir(edit)

    def refresh_source_items(self):
        return refresh_source_items(self)

    def _dataset_split_dir(self, split: str) -> Path:
        return dataset_split_dir(self, split)

    def _scope_target_path(self, scope: str) -> Path:
        return scope_target_path_for_page(self, scope)

    def _folder_source_path_for_selection(self) -> str:
        return folder_source_path_for_page(self)

    def on_show(self):
        self.refresh_model_choices(self.app.settings["validation"].get("model_path", ""))
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
