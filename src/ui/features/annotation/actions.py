from __future__ import annotations

from pathlib import Path

from src.services.annotation.history import restore_annotations, snapshot_annotations


class AnnotationActionsMixin:
    def _copy_annotations(self):
        return restore_annotations(snapshot_annotations(self.canvas.annotations))

    def record_annotation_history(self, before, after, focus_index) -> None:
        if self.current_image_path is None:
            return
        self.annotation_history.record(
            self.current_image_path,
            before,
            after,
            focus_index,
        )
        self._refresh_manual_action_buttons()

    def clear_annotation_history(self) -> None:
        self.annotation_history.clear()
        self._refresh_manual_action_buttons()

    def _restore_history_state(self, entry, values) -> None:
        target = entry.image_path.resolve()
        target_index = next(
            (
                index
                for index, image_path in enumerate(self.image_items)
                if image_path.resolve() == target
            ),
            -1,
        )
        if target_index < 0:
            self.clear_annotation_history()
            return
        if target_index != self.current_index:
            self.change_current_index(target_index)
        self.canvas._reset_transient_draw_state()
        self.canvas.annotations = restore_annotations(values)
        if self.canvas.draw_shape == "select" and entry.focus_index is not None:
            selected_index = entry.focus_index
            if not 0 <= selected_index < len(self.canvas.annotations):
                selected_index = -1
        else:
            selected_index = -1
        self.canvas.selected_index = selected_index
        self.canvas.hovered_index = selected_index
        self.canvas.hovered_handle = None
        self.canvas._emit_selection()
        self.canvas._update_hover_cursor()
        self.mark_dirty_and_save()
        self.canvas.update()

    def undo_annotation_change(self) -> None:
        entry = self.annotation_history.pop_undo()
        if entry is not None:
            self._restore_history_state(entry, entry.before)

    def redo_annotation_change(self) -> None:
        entry = self.annotation_history.pop_redo()
        if entry is not None:
            self._restore_history_state(entry, entry.after)

    def save_current_labelme(self) -> None:
        self.save_current(force=True, save_json=True, save_yolo=False)

    def save_current_yolo(self) -> None:
        if (
            self.yolo_auto_save_enabled()
            or self.current_image_path is None
            or self.output_mode not in {"detect", "obb", "seg"}
        ):
            return
        self.save_current(force=True, save_json=False, save_yolo=True)

    def save_current_default(self) -> None:
        if self.labelme_auto_save_enabled() or self.current_image_path is None:
            return
        self.save_current_labelme()

    def undo_unsaved_changes(self) -> None:
        self.undo_annotation_change()

    def _refresh_manual_action_buttons(self) -> None:
        has_current = self.current_image_path is not None and self.canvas.image_size != (0, 0)
        use_separate_save_actions = self.show_yolo_save_in_context_menu()
        can_save_labelme = has_current and not self.labelme_auto_save_enabled()
        can_save_yolo = (
            has_current
            and use_separate_save_actions
            and not self.yolo_auto_save_enabled()
            and self.output_mode in {"detect", "obb", "seg"}
        )
        self.canvas.save_labelme_callback = self.save_current_labelme
        self.canvas.save_yolo_callback = self.save_current_yolo
        self.canvas.save_default_callback = self.save_current_default
        self.canvas.undo_callback = self.undo_annotation_change
        self.canvas.redo_callback = self.redo_annotation_change
        self.canvas.can_save_default = (
            has_current and not use_separate_save_actions and not self.labelme_auto_save_enabled()
        )
        self.canvas.can_save_labelme = can_save_labelme
        self.canvas.can_save_yolo = can_save_yolo
        self.canvas.can_undo = has_current and self.annotation_history.can_undo
        self.canvas.can_redo = has_current and self.annotation_history.can_redo
        self.canvas.show_separate_yolo_save = use_separate_save_actions

    def clear_annotations_for_image(self, image_path: Path) -> None:
        self._remove_annotation_files(image_path)
        if self.current_image_path == image_path:
            self.canvas.annotations = []
            self.canvas.selected_index = -1
            self.labelme_dirty = False
            self.yolo_dirty = False
            self._sync_dirty_flag()
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
            self.labelme_dirty = False
            self.yolo_dirty = False
            self._sync_dirty_flag()
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
