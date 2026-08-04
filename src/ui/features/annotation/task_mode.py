from __future__ import annotations

from src.services.annotation import detect_yolo_mode
from src.services.annotation.yolo_format import YOLO_MODES


class AnnotationTaskModeMixin:
    def _task_mode_probe_signature(self) -> tuple[str, str]:
        return (str(self.path_from_setting("images_dir").resolve()), str(self.path_from_setting("labels_dir").resolve()))

    def _refresh_task_mode_from_paths(self, *, force: bool = False) -> None:
        signature = self._task_mode_probe_signature()
        if not force and signature == self._mode_probe_signature:
            return
        previous_signature = self._mode_probe_signature
        self._mode_probe_signature = signature
        detected = detect_yolo_mode(self.path_from_setting("labels_dir"))
        settings_task = self.context.settings.task
        if detected in YOLO_MODES:
            self.output_mode = detected
            settings_task.mode = detected
            settings_task.mode_selected = True
        elif settings_task.mode_selected and self.output_mode in YOLO_MODES and previous_signature is None and not force:
            pass
        else:
            self.output_mode = None
            settings_task.mode_selected = False
        self.save_settings()
        self._refresh_task_mode_controls()

    def _refresh_task_mode_controls(self) -> None:
        if not hasattr(self, "output_mode_combo"):
            return
        visible = self.yolo_features_enabled()
        self.output_mode_label.setVisible(visible)
        self.output_mode_combo.setVisible(visible)
        self.output_mode_combo.blockSignals(True)
        if self.output_mode in YOLO_MODES:
            self.output_mode_combo.setCurrentText(self.output_mode)
            self.output_mode_combo.setStyleSheet("")
        else:
            self.output_mode_combo.setCurrentIndex(-1)
            self.output_mode_combo.setPlaceholderText("未选择")
            self.output_mode_combo.setStyleSheet("color: #C62828;")
        self.output_mode_combo.blockSignals(False)

    def on_setting_changed(self, keys, value):
        if keys == ("paths", "images_dir"):
            self.clear_annotation_history()
            self._refresh_task_mode_from_paths(force=True)
            self.scan_images(select_first=True)
        elif keys == ("paths", "annotations_dir"):
            self.clear_annotation_history()
            self.load_current()
            self.refresh_file_list()
        elif keys == ("paths", "labels_dir"):
            self.clear_annotation_history()
            self._refresh_task_mode_from_paths(force=True)
            self.load_current()
            self.refresh_file_list()

    def change_output_mode(self, text: str) -> None:
        mode = text if text in YOLO_MODES else None
        if mode is None:
            return
        self.output_mode = mode
        self.context.settings.task.mode = mode
        self.context.settings.task.mode_selected = True
        self.save_settings()
        if self.current_image_path is not None and self.canvas.annotations:
            self.yolo_dirty = True
            if self.yolo_auto_save_enabled():
                self.save_current(save_json=False, save_yolo=True)
        self._refresh_task_mode_controls()
        self.refresh_annotation_list()
        self._refresh_manual_action_buttons()


__all__ = ["AnnotationTaskModeMixin"]
