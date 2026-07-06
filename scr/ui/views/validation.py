from __future__ import annotations

import os
import threading
from pathlib import Path
from queue import Queue

from scr.ui.page_base import BasePage
from scr.ui.qt import QComboBox, QFileDialog, QLineEdit, QPushButton, QTimer
from scr.ui.views.validation_helpers import (
    ResultNavigator,
    ValidationYamlPatch,
)
from scr.ui.views.validation_layout import build_validation_layout
from scr.ui.views.validation_runtime import (
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
from scr.ui.views.validation_result_list import show_validation_result_list
from scr.ui.views.validation_results import (
    handle_detection_result,
    show_cached_source_result as show_cached_validation_source_result,
    show_detection_payload as show_detection_result_payload,
)
from scr.ui.views.validation_state import (
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
    val_override_value_for_scope,
)
from scr.ui.views.validation_sources import SOURCE_SCOPE_OPTIONS
from scr.ui.workers import DetectionWorker


class ValidatePage(BasePage):
    def __init__(self, app):
        super().__init__(app)
        self.detect_results = []
        self.detect_index = -1
        self.detect_stop = threading.Event()
        self.detect_worker = None
        self.is_detecting = False
        self.is_batch_detection = False
        self._all_model_paths: list[Path] = []
        self._model_display_paths: dict[str, Path] = {}
        self.source_items: list[Path] = []
        self.source_index = -1
        self.result_by_source: dict[str, dict] = {}
        self.user_selected_result = False
        self.result_nav_buttons: list[QPushButton] = []
        self.log_queue: Queue | None = None
        self.stop_requested = False
        self.validation_yaml_patch = ValidationYamlPatch()
        self.result_navigator = ResultNavigator(
            lambda: self.detect_results,
            lambda: self.detect_index,
            lambda index: setattr(self, "detect_index", index),
            lambda selected: setattr(self, "user_selected_result", selected),
            self.show_detection_payload,
        )
        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(150)
        self.poll_timer.timeout.connect(self.poll_validation_queue)
        build_validation_layout(self, app)

        self.mode_combo.currentTextChanged.connect(self.update_source_mode)
        self.update_source_mode(self.mode_combo.currentText())
        self.update_detection_button_text()

    def update_source_mode(self, value):
        return update_source_mode(self, value)

    def is_val_mode(self, value: str | None = None) -> bool:
        return str(value or self.mode_combo.currentText()).strip() == "数据集验证"

    def _configure_source_combo(
        self, values: list[str], current_text: str, placeholder: str
    ) -> None:
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
        mode = self.mode_combo.currentText()
        if self.is_val_mode(mode):
            self.start_det_btn.setText("开始验证")
            self.stop_det_btn.setText("停止")
            return
        self.start_det_btn.setText("开始检测" if mode == "图片/视频" else "批量检测")
        self.stop_det_btn.setText("停止")

    def choose_detection_source(self, combo: QComboBox):
        current_text = combo.currentText().strip()
        current = (
            self.resolve_combo_path_text(current_text)
            if current_text and current_text not in SOURCE_SCOPE_OPTIONS
            else str(self.project_root())
        )
        if self.mode_combo.currentText() == "图片/视频":
            path, _ = QFileDialog.getOpenFileName(
                self,
                "选择图片或视频",
                current,
                "图片/视频 (*.jpg *.jpeg *.png *.bmp *.mp4 *.avi *.mov *.mkv);;所有文件 (*)",
            )
            if path:
                combo.setCurrentText(self.display_path(path))
                self.refresh_source_items()
            return
        path = QFileDialog.getExistingDirectory(self, "选择图片文件夹", current)
        if path:
            combo.setCurrentText(self.display_path(path))
            self.refresh_source_items()

    def choose_dataset_yaml(self, edit: QLineEdit):
        current = self.resolve_path_text(edit) if edit.text() else str(self.project_root())
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择数据集 YAML",
            current,
            "YAML 文件 (*.yaml *.yml);;所有文件 (*)",
        )
        if path:
            edit.setText(self.display_path(path))

    def choose_output_dir(self, edit: QLineEdit):
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

    # Task 9: Only allow one detection at a time
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

    def show_detection_payload(self, payload):
        show_detection_result_payload(self, payload)

    def first_result(self):
        self.result_navigator.show_first()

    def last_result(self):
        self.result_navigator.show_last()

    def prev_result(self):
        self.result_navigator.show_previous()

    def next_result(self):
        self.result_navigator.show_next()

    def show_source_index(self, index: int):
        self.refresh_source_items()
        if not self.source_items:
            return
        self.source_index = index % len(self.source_items)

    def show_cached_source_result(self, path: Path) -> bool:
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

# ===================================================================
#  Task 13: Settings page - system info style + auto-refresh
#  Task 10: Custom command toggle
# ===================================================================
