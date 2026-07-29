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


class ValidationSourceActionsMixin:
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
        validation = self.context.settings.validation
        saved_selection = validation.source_selection
        current = (
            validation.source_path
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


