from __future__ import annotations


_SHAPE_LABELS = {
    "rect": "矩形框",
    "circle": "圆形",
    "obb": "有向矩形",
    "obb_mirror": "镜像有向矩形",
    "obb_single": "有向矩形",
    "polygon": "多边形",
    "line_expand": "直线拓展",
}


class AnnotationClassPanelMixin:
    def class_names(self) -> list[str]:
        names = [
            str(name).strip()
            for name in self.app.settings.get("dataset", {}).get("class_names", [])
            if str(name).strip()
        ]
        return names

    def _refresh_class_state(self) -> None:
        names = self.class_names()
        self.current_class_id = (
            min(max(self.current_class_id, 0), len(names) - 1) if names else 0
        )
        if hasattr(self, "class_combo"):
            self.class_combo.blockSignals(True)
            self.class_combo.clear()
            self.class_combo.addItems(names)
            self.class_combo.setCurrentIndex(self.current_class_id)
            self.class_combo.blockSignals(False)
        if hasattr(self, "canvas"):
            self.canvas.set_current_class(self.current_class_id)
            self.canvas.set_class_names(names)
            annotation_settings = self.app.settings.get("annotation", {})
            self.canvas.set_line_expand_config(
                annotation_settings.get("line_expand_enabled", False),
                annotation_settings.get("line_expand_pixels", 10),
            )
            self.canvas.set_interaction_config(
                annotation_settings.get("continuous_draw", False),
                annotation_settings.get("quick_draw", True),
            )
            self.canvas.set_show_annotation_names(
                annotation_settings.get("show_annotation_names", False)
            )
            self.canvas.set_show_canvas_status(
                annotation_settings.get("show_canvas_status", True)
            )

    def refresh_annotation_list(self) -> None:
        names = self.class_names()
        self.annotation_list.blockSignals(True)
        self.annotation_list.clear()
        for index, annotation in enumerate(self.canvas.annotations):
            label = (
                names[annotation.class_id]
                if 0 <= annotation.class_id < len(names)
                else str(annotation.class_id)
            )
            shape_text = _SHAPE_LABELS.get(annotation.shape, annotation.shape)
            format_text = (
                "obb"
                if annotation.shape in {"obb", "obb_mirror", "obb_single", "line_expand"}
                else "detect"
            )
            item = self._list_widget_item_factory(
                f"{index + 1}.{label}-{shape_text}（{format_text}）"
            )
            self.annotation_list.addItem(item)
        self.annotation_list.setCurrentRow(self.canvas.selected_index)
        self.annotation_list.blockSignals(False)
        self._update_current_file_list_item()
