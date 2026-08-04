from __future__ import annotations

from src.shared.qt import QEvent, QTimer, Qt
from src.ui.features.annotation.layout import set_annotation_bottom_margin


class AnnotationLifecycleMixin:
    def delete_selected(self) -> None:
        self.canvas.delete_selected()

    def keyPressEvent(self, event):  # noqa: N802 - Qt API name
        if event.key() == Qt.Key.Key_Delete:
            self.delete_selected()
            return
        if event.key() == Qt.Key.Key_A:
            self.prev_image()
            return
        if event.key() == Qt.Key.Key_D:
            self.next_image()
            return
        super().keyPressEvent(event)

    def on_show(self) -> None:
        self._refresh_task_mode_from_paths()
        self.sam_assist.refresh_models()
        self.refresh_annotation_status_bar()
        self._refresh_path_labels()
        if not self._initialized_once:
            self._initialized_once = True
            if not self.image_items:
                QTimer.singleShot(0, self, lambda: self.scan_images(select_first=True))
                return
        decorate_rows = getattr(self, "_decorate_visible_rows", None)
        if callable(decorate_rows):
            decorate_rows()
        if not self.image_items:
            self.scan_images(select_first=True)

    def prepare_for_first_show(self) -> None:
        if self.image_items:
            return
        prepare_initial_image = getattr(self, "prepare_initial_image", None)
        if callable(prepare_initial_image):
            prepare_initial_image()

    def on_hide(self) -> None:
        self.sam_assist.shutdown(wait=False)
        self.annotation_status_bar.hide()
        set_annotation_bottom_margin(self, 12)

    def prepare_for_show(self) -> None:
        self.refresh_annotation_status_bar(page_visible=True)

    def refresh_annotation_status_bar(self, *, page_visible: bool | None = None) -> None:
        show_status = bool(self.context.settings.annotation.show_canvas_status)
        if show_status:
            self.annotation_status_bar.showMessage(f"当前状态：{self.canvas._canvas_status_text()}")
        page_visible = self.isVisible() if page_visible is None else page_visible
        status_visible = show_status and page_visible
        self.annotation_status_bar.setVisible(status_visible)
        set_annotation_bottom_margin(self, 0 if status_visible else 12)

    def has_unsaved_annotations(self) -> bool:
        return bool(self._current_image_unsaved_text())

    def on_shutdown(self) -> None:
        self.sam_assist.shutdown(wait=True)

    def eventFilter(self, watched, event):  # noqa: N802 - Qt API name
        if watched is self.file_list.viewport() and event.type() in {QEvent.Type.Paint, QEvent.Type.Resize, QEvent.Type.Wheel}:
            decorate_rows = getattr(self, "_decorate_visible_rows", None)
            if callable(decorate_rows):
                QTimer.singleShot(0, self, decorate_rows)
        return super().eventFilter(watched, event)


__all__ = ["AnnotationLifecycleMixin"]
