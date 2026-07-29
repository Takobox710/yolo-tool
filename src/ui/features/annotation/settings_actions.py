from __future__ import annotations

from pathlib import Path

from src.services.annotation import collect_labelme_class_counts, convert_labelme_classes
from src.services.data_ops import resolve_project_path
from src.shared.qt import QDialog
from src.ui.features.annotation.ai.dialog import AiPrelabelDialog
from src.ui.features.annotation.dialogs import (
    AnnotationSettingsDialog,
    ClassManagerDialog,
    DrawShapeDialog,
)


class AnnotationPageSettingsMixin:
    def enable_draw_mode(self) -> None:
        self.sam_assist.refresh_models()
        dialog = DrawShapeDialog(
            self.canvas.line_expand_enabled,
            self,
            sam_models=self.sam_assist.models,
            selected_sam_model=(
                self.sam_assist.selected_model.key
                if self.sam_assist.selected_model is not None
                else ""
            ),
            sam_enabled=self.sam_assist.enabled,
            sam_toggle_callback=self.sam_assist.set_enabled,
            sam_model_callback=self.sam_assist.select_model,
            sam_settings=self.sam_assist.parameters(),
            sam_settings_callback=self.sam_assist.apply_parameters,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if dialog.selected_sam_model:
            self.sam_assist.select_model(dialog.selected_sam_model)
        self.sam_assist.set_enabled(dialog.sam_enabled)
        self.canvas.set_draw_shape(dialog.selected_shape)
        self.canvas.setFocus()

    def open_ai_prelabel_dialog(self) -> None:
        dialog = AiPrelabelDialog(self, self)
        dialog.exec()

    def open_annotation_settings(self) -> None:
        current = self.context.settings.annotation
        previous_labels_dir = self.path_from_setting("labels_dir")
        previous_load_yolo = current.load_yolo_when_labelme_missing
        dialog = AnnotationSettingsDialog(
            current.line_expand_enabled,
            current.line_expand_pixels,
            current.auto_save,
            current.auto_convert_yolo,
            current.show_yolo_save_in_context_menu,
            current.continuous_draw,
            current.quick_draw,
            self.display_path(self.path_from_setting("labels_dir")),
            self,
            load_yolo_when_labelme_missing=current.load_yolo_when_labelme_missing,
            show_annotation_names=current.show_annotation_names,
            show_canvas_status=current.show_canvas_status,
            optimize_mirror_edit=current.optimize_mirror_edit,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        (
            enabled,
            pixels,
            auto_save,
            auto_convert_yolo,
            load_yolo_when_labelme_missing,
            show_yolo_save_in_context_menu,
            continuous_draw,
            quick_draw,
            yolo_dir,
            show_annotation_names,
            show_canvas_status,
            optimize_mirror_edit,
        ) = dialog.values()
        current.line_expand_enabled = enabled
        current.line_expand_pixels = pixels
        current.auto_save = auto_save
        current.auto_convert_yolo = auto_convert_yolo
        current.load_yolo_when_labelme_missing = load_yolo_when_labelme_missing
        current.show_yolo_save_in_context_menu = show_yolo_save_in_context_menu
        current.continuous_draw = continuous_draw
        current.quick_draw = quick_draw
        current.show_annotation_names = show_annotation_names
        current.show_canvas_status = show_canvas_status
        current.optimize_mirror_edit = optimize_mirror_edit
        if yolo_dir:
            resolved_yolo_dir = Path(resolve_project_path(yolo_dir, self.project_root()))
            self.context.settings.paths.labels_dir = str(resolved_yolo_dir)
            resolved_yolo_dir.mkdir(parents=True, exist_ok=True)
        self.save_settings()
        labels_dir_changed = self.path_from_setting("labels_dir") != previous_labels_dir
        load_yolo_changed = (
            current.load_yolo_when_labelme_missing != previous_load_yolo
        )
        if labels_dir_changed:
            self._refresh_task_mode_from_paths(force=True)
        self._refresh_class_state()
        self._refresh_manual_action_buttons()
        self._refresh_task_mode_controls()
        self.refresh_annotation_list()
        if labels_dir_changed or load_yolo_changed:
            self.load_current()
        if auto_save or auto_convert_yolo:
            self.save_current(
                force=True,
                save_json=auto_save,
                save_yolo=auto_convert_yolo,
            )

    def manage_classes(self) -> None:
        self._sync_project_labelme_class_names()
        class_names = self.class_names()
        dialog = ClassManagerDialog(
            class_names,
            self,
            annotations=self.canvas.annotations,
            annotation_counts=collect_labelme_class_counts(
                self.path_from_setting("annotations_dir"), class_names
            ),
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if dialog.annotation_class_ids_changed:
            for annotation, class_id in zip(
                self.canvas.annotations, dialog.annotation_class_ids
            ):
                annotation.class_id = class_id
        operations = dialog.conversion_operations
        if operations and self.current_image_path is not None and self.dirty:
            self.save_current(force=True, save_json=True)
        self.context.settings.dataset.class_names = dialog.class_names
        self.save_settings()
        for source_name, target_name in operations:
            convert_labelme_classes(
                self.path_from_setting("annotations_dir"), source_name, target_name
            )
        self._refresh_class_state()
        self.canvas.set_class_names(dialog.class_names)
        self.refresh_annotation_list()
        if dialog.annotation_class_ids_changed:
            if operations and self.current_image_path is not None:
                self.load_current()
            else:
                self.mark_dirty_and_save()
        else:
            self.canvas.update()
