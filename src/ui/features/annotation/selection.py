from __future__ import annotations


class AnnotationSelectionMixin:
    def prev_image(self) -> None:
        if not self.image_items:
            self.scan_images(select_first=True)
            return
        self.change_current_index((self.current_index - 1) % len(self.image_items))

    def next_image(self) -> None:
        if not self.image_items:
            self.scan_images(select_first=True)
            return
        self.change_current_index((self.current_index + 1) % len(self.image_items))

    def jump_to_file(self, row: int) -> None:
        if 0 <= row < len(self.image_items) and row != self.current_index:
            self.change_current_index(row)

    def change_current_index(self, index: int) -> None:
        self.save_current()
        self.current_index = index
        ensure_items = getattr(self, "_ensure_file_list_items", None)
        if callable(ensure_items):
            ensure_items(index + 1)
        self.file_list.blockSignals(True)
        self.file_list.setCurrentRow(index)
        self.file_list.blockSignals(False)
        self._update_file_count_label()
        self.load_current()

    def change_class(self, index: int) -> None:
        self.current_class_id = max(0, index)
        self.canvas.set_current_class(self.current_class_id)
        selected_index = self.canvas.selected_index
        if not (0 <= selected_index < len(self.canvas.annotations)):
            return
        annotation = self.canvas.annotations[selected_index]
        if annotation.class_id == self.current_class_id:
            return
        annotation.class_id = self.current_class_id
        self.mark_dirty_and_save()
        self.canvas.update()

    def change_shape(self, text: str) -> None:
        mapping = {
            "矩形框": "rect",
            "圆形": "circle",
            "镜像有向矩形": "obb_mirror",
            "有向矩形": "obb_single",
            "多边形": "polygon",
            "直线扩展": "line_expand",
        }
        self.canvas.set_draw_shape(mapping.get(text, "rect"))

    def select_annotation(self, row: int) -> None:
        if row != self.canvas.selected_index:
            self.canvas.selected_index = row
        self._sync_target_type_to_selection()
        self.canvas.update()

    def sync_selection(self, row: int) -> None:
        self.annotation_list.blockSignals(True)
        self.annotation_list.setCurrentRow(row)
        self.annotation_list.blockSignals(False)
        self._sync_target_type_to_selection()

    def _sync_target_type_to_selection(self) -> None:
        selected_index = self.canvas.selected_index
        if not (0 <= selected_index < len(self.canvas.annotations)):
            return
        class_id = self.canvas.annotations[selected_index].class_id
        self.current_class_id = max(0, class_id)
        self.canvas.set_current_class(self.current_class_id)
        if not hasattr(self, "class_combo"):
            return
        if not 0 <= class_id < self.class_combo.count():
            return
        self.class_combo.blockSignals(True)
        self.class_combo.setCurrentIndex(class_id)
        self.class_combo.blockSignals(False)
