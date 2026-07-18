from __future__ import annotations

from pathlib import Path

from src.shared.qt import QDialog
from src.ui.features.annotation.ai.dialog import AiPrelabelDialog
from src.ui.features.annotation.dialogs import (
    AnnotationSettingsDialog,
    ClassManagerDialog,
    DrawShapeDialog,
)


class AnnotationPageSettingsMixin:
    def enable_draw_mode(self) -> None:
        dialog = DrawShapeDialog(self.canvas.line_expand_enabled, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.canvas.set_draw_shape(dialog.selected_shape)
        self.canvas.setFocus()

    def open_ai_prelabel_dialog(self) -> None:
        dialog = AiPrelabelDialog(self, self)
        dialog.exec()

    def open_annotation_settings(self) -> None:
        current = self.app.settings.get("annotation", {})
        dialog = AnnotationSettingsDialog(
            current.get("line_expand_enabled", False),
            current.get("line_expand_pixels", 10),
            current.get("auto_save", True),
            current.get("auto_convert_yolo", False),
            current.get("show_yolo_save_in_context_menu", False),
            current.get("continuous_draw", False),
            current.get("quick_draw", True),
            str(self.path_from_setting("labels_dir")),
            self,
            show_annotation_names=current.get("show_annotation_names", False),
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        (
            enabled,
            pixels,
            auto_save,
            auto_convert_yolo,
            show_yolo_save_in_context_menu,
            continuous_draw,
            quick_draw,
            yolo_dir,
            show_annotation_names,
        ) = dialog.values()
        self.app.settings.setdefault("annotation", {})["line_expand_enabled"] = enabled
        self.app.settings["annotation"]["line_expand_pixels"] = pixels
        self.app.settings["annotation"]["auto_save"] = auto_save
        self.app.settings["annotation"]["auto_convert_yolo"] = auto_convert_yolo
        self.app.settings["annotation"]["show_yolo_save_in_context_menu"] = (
            show_yolo_save_in_context_menu
        )
        self.app.settings["annotation"]["continuous_draw"] = continuous_draw
        self.app.settings["annotation"]["quick_draw"] = quick_draw
        self.app.settings["annotation"]["show_annotation_names"] = show_annotation_names
        if yolo_dir:
            self.app.settings.setdefault("paths", {})["labels_dir"] = yolo_dir
            Path(yolo_dir).mkdir(parents=True, exist_ok=True)
        self.save_settings()
        self._refresh_class_state()
        self._refresh_manual_action_buttons()
        if auto_save or auto_convert_yolo:
            self.save_current(
                force=True,
                save_json=auto_save,
                save_yolo=auto_convert_yolo,
            )

    def manage_classes(self) -> None:
        dialog = ClassManagerDialog(self.class_names(), self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.app.settings.setdefault("dataset", {})["class_names"] = dialog.class_names
        self.save_settings()
        self._refresh_class_state()
        self.canvas.set_class_names(dialog.class_names)
        self.refresh_annotation_list()
