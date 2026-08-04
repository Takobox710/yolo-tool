from __future__ import annotations

from pathlib import Path

from src.services.annotation import collect_annotation_presence
from src.shared.qt import Qt
from src.ui.features.annotation.file_item import ANNOTATION_CHECKED_ROLE
from src.ui.shared.workers import Worker


class AnnotationStatusScanMixin:
    def _has_annotation_for_image(self, image_path: Path) -> bool:
        cached = self._annotation_statuses.get(self._annotation_status_key(image_path))
        if cached is not None:
            return cached
        return self.current_image_path == image_path and bool(self.canvas.annotations)

    @staticmethod
    def _annotation_status_key(image_path: Path) -> str:
        return str(Path(image_path).resolve())

    def _start_annotation_status_scan(self, request_id: int, already_scanned_paths: list[Path]) -> None:
        remaining_paths = self.image_items[len(already_scanned_paths) :]
        if not remaining_paths:
            return
        self._annotation_status_worker = Worker(
            "annotation_file_status",
            lambda request_id=request_id, paths=list(remaining_paths): {
                "request_id": request_id,
                "statuses": collect_annotation_presence(paths, self.path_from_setting("annotations_dir"), self.path_from_setting("labels_dir")),
            },
        )
        self._annotation_status_worker.finished_with_payload.connect(self._handle_annotation_status_payload)
        self._annotation_status_worker.finished.connect(self._clear_annotation_status_worker)
        self._annotation_status_worker.start()

    def _handle_annotation_status_payload(self, kind: str, payload) -> None:
        if kind != "annotation_file_status" or not isinstance(payload, dict):
            return
        if payload.get("request_id") != self._annotation_status_request_id:
            return
        self._annotation_statuses.update(payload.get("statuses") or {})
        self._apply_visible_annotation_statuses()

    def _apply_visible_annotation_statuses(self) -> None:
        for row in range(min(self._file_list_rendered_count, len(self.image_items))):
            item = self.file_list.item(row)
            if item is None:
                continue
            path = self.image_items[row]
            item.setData(ANNOTATION_CHECKED_ROLE, self._has_annotation_for_image(path) or (path == self.current_image_path and bool(self.canvas.annotations)))
            self._sync_visible_file_item_widget(row)

    def _clear_annotation_status_worker(self) -> None:
        self._annotation_status_worker = None

    def _cancel_annotation_status_scan(self) -> None:
        worker = self._annotation_status_worker
        if worker is None:
            return
        worker.finished_with_payload.disconnect(self._handle_annotation_status_payload)
        worker.finished.disconnect(self._clear_annotation_status_worker)
        worker.wait(50)
        self._annotation_status_worker = None

    def _current_image_has_annotations(self) -> bool:
        return bool(self.canvas.annotations)

    def _current_image_has_unsaved_changes(self) -> bool:
        return bool(self._current_image_unsaved_text())

    def _current_image_unsaved_text(self) -> str:
        if self.current_image_path is None:
            return ""
        labelme_dirty = bool(self.labelme_dirty)
        yolo_dirty = bool(self.yolo_dirty and self.show_yolo_save_in_context_menu())
        if not self.show_yolo_save_in_context_menu():
            return "未保存" if labelme_dirty and not self.labelme_auto_save_enabled() else ""
        if labelme_dirty and yolo_dirty:
            return "两种格式标注均未保存"
        if labelme_dirty:
            return "Labelme标注未保存"
        if yolo_dirty:
            return "YOLO标注未保存"
        return ""


__all__ = ["AnnotationStatusScanMixin"]
