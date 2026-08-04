from __future__ import annotations

from pathlib import Path

from src.services.annotation import collect_annotation_presence, scan_annotation_image_items
from src.ui.features.annotation.annotation_status_scan import AnnotationStatusScanMixin
from src.ui.features.annotation.file_list_render import AnnotationFileListRenderMixin


class AnnotationFileBrowserMixin(AnnotationFileListRenderMixin, AnnotationStatusScanMixin):
    """Compatibility façade coordinating image scan, list rendering and status workers."""

    def scan_images(self, *, select_first: bool) -> None:
        self.clear_annotation_history()
        self._sync_project_labelme_class_names()
        image_dir = self.path_from_setting("images_dir")
        self.image_items = scan_annotation_image_items(image_dir)
        self._annotation_status_request_id += 1
        self._cancel_annotation_status_scan()
        self._file_list_render_timer.stop()
        self._annotation_statuses = {}
        if select_first and self.image_items:
            self.current_index = 0
        elif self.current_index >= len(self.image_items):
            self.current_index = 0 if self.image_items else -1
        initial_count = self._initial_file_render_count()
        sync_paths = self.image_items[:initial_count]
        if sync_paths:
            self._annotation_statuses.update(collect_annotation_presence(sync_paths, self.path_from_setting("annotations_dir"), self.path_from_setting("labels_dir")))
        self.refresh_file_list()
        if self.current_index >= 0:
            self._ensure_file_list_items(self.current_index + 1)
            self.file_list.setCurrentRow(self.current_index)
            self.load_current()
        else:
            self._update_file_count_label()
            self.canvas.set_image(None, [], self.class_names())
        self._schedule_remaining_file_list_render()
        self._start_annotation_status_scan(self._annotation_status_request_id, sync_paths)
        self._refresh_manual_action_buttons()

    def prepare_initial_image(self) -> None:
        self._sync_project_labelme_class_names()
        if self.image_items:
            return
        image_dir = self.path_from_setting("images_dir")
        self.image_items = scan_annotation_image_items(image_dir)
        if not self.image_items:
            self.current_index = -1
            return
        self._annotation_status_request_id += 1
        self._cancel_annotation_status_scan()
        self._file_list_render_timer.stop()
        self.current_index = 0
        self._annotation_statuses = {}
        sync_paths = self.image_items[: self._initial_file_render_count()]
        if sync_paths:
            self._annotation_statuses.update(collect_annotation_presence(sync_paths, self.path_from_setting("annotations_dir"), self.path_from_setting("labels_dir")))
        self.refresh_file_list()
        self.file_list.setCurrentRow(self.current_index)
        self.load_current()
        self._schedule_remaining_file_list_render()
        self._start_annotation_status_scan(self._annotation_status_request_id, sync_paths)


__all__ = ["AnnotationFileBrowserMixin"]
