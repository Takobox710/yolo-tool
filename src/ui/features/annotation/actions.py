from __future__ import annotations

from pathlib import Path


class AnnotationActionsMixin:
    def save_current_labelme(self) -> None:
        self.save_current(force=True, save_json=True, save_yolo=False)

    def save_current_yolo(self) -> None:
        if self.yolo_auto_save_enabled() or self.current_image_path is None:
            return
        self.save_current(force=True, save_json=False, save_yolo=True)

    def save_current_default(self) -> None:
        if self.labelme_auto_save_enabled() or self.current_image_path is None:
            return
        self.save_current_labelme()

    def undo_unsaved_changes(self) -> None:
        if not self.dirty:
            return
        self.load_current()

    def _refresh_manual_action_buttons(self) -> None:
        has_current = self.current_image_path is not None and self.canvas.image_size != (0, 0)
        use_separate_save_actions = self.show_yolo_save_in_context_menu()
        can_save_labelme = has_current and not self.labelme_auto_save_enabled()
        can_save_yolo = (
            has_current
            and use_separate_save_actions
            and not self.yolo_auto_save_enabled()
        )
        self.canvas.save_labelme_callback = self.save_current_labelme
        self.canvas.save_yolo_callback = self.save_current_yolo
        self.canvas.save_default_callback = self.save_current_default
        self.canvas.undo_callback = self.undo_unsaved_changes
        self.canvas.can_save_default = (
            has_current and not use_separate_save_actions and not self.labelme_auto_save_enabled()
        )
        self.canvas.can_save_labelme = can_save_labelme
        self.canvas.can_save_yolo = can_save_yolo
        self.canvas.can_undo = has_current and self.dirty
        self.canvas.show_separate_yolo_save = use_separate_save_actions

    def clear_annotations_for_image(self, image_path: Path) -> None:
        self._remove_annotation_files(image_path)
        if self.current_image_path == image_path:
            self.canvas.annotations = []
            self.canvas.selected_index = -1
            self.dirty = False
            self.refresh_annotation_list()
            self.canvas.update()
        self.refresh_file_list()
        if self.current_image_path == image_path and self.current_index >= 0:
            self.load_current()

    def delete_image_and_annotations(self, image_path: Path) -> None:
        self._remove_annotation_files(image_path)
        if image_path.exists():
            image_path.unlink()
        if self.current_image_path == image_path:
            self.dirty = False
            self.current_image_path = None
            self.current_json_path = None
            self.current_yolo_path = None
        try:
            removed_index = self.image_items.index(image_path)
        except ValueError:
            removed_index = -1
        if removed_index >= 0 and self.current_index > removed_index:
            self.current_index -= 1
        self.scan_images(select_first=False)
