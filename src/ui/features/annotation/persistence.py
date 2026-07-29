from __future__ import annotations

from pathlib import Path

from PIL import Image

from src.services.annotation import (
    collect_labelme_class_names,
    load_editable_annotations,
    load_labelme_annotations,
    save_editable_annotations,
    save_labelme_annotations,
)
from src.services.annotation.yolo_format import detect_yolo_mode, infer_yolo_file_mode


class AnnotationPersistenceMixin:
    def _sync_dirty_flag(self) -> None:
        self.dirty = bool(self.labelme_dirty or self.yolo_dirty)

    def _current_yolo_source_mode(self, yolo_path: Path) -> str | None:
        mode = infer_yolo_file_mode(yolo_path)
        if mode == "ambiguous":
            mode = detect_yolo_mode(self.path_from_setting("labels_dir"))
        return mode if mode in {"detect", "obb", "seg"} else None

    def _yolo_needs_save(self, yolo_path: Path, annotations: list[EditableAnnotation]) -> bool:
        if not self.yolo_features_enabled() or not self.output_mode:
            return False
        if not annotations:
            return False
        if not yolo_path.exists():
            return True
        source_mode = self._current_yolo_source_mode(yolo_path)
        return source_mode != self.output_mode

    def _sync_project_labelme_class_names(self) -> None:
        names = collect_labelme_class_names(
            self.path_from_setting("annotations_dir"), self.class_names()
        )
        if names == self.class_names():
            return
        self.context.settings.dataset.class_names = names
        self.save_settings()
        self._refresh_class_state()

    def load_current(self) -> None:
        if not (0 <= self.current_index < len(self.image_items)):
            return
        self._sync_project_labelme_class_names()
        image_path = self.image_items[self.current_index]
        json_path = self.path_from_setting("annotations_dir") / f"{image_path.stem}.json"
        yolo_path = self.path_from_setting("labels_dir") / f"{image_path.stem}.txt"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        yolo_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with Image.open(image_path) as image:
                image_size = image.size
        except OSError as exc:
            self._show_image_open_error(exc)
            return
        if json_path.exists():
            annotations, class_names = load_labelme_annotations(
                image_size,
                json_path,
                self.class_names(),
                self.context.settings.annotation.line_expand_pixels,
            )
            if class_names != self.class_names():
                self.context.settings.dataset.class_names = class_names
                self.save_settings()
                self._refresh_class_state()
        elif self.load_yolo_when_labelme_missing() and yolo_path.exists():
            source_mode = self._current_yolo_source_mode(yolo_path) or self.output_mode
            annotations = load_editable_annotations(
                image_size,
                yolo_path,
                task_mode=source_mode or "detect",
            )
        else:
            annotations = []

        self.current_json_path = json_path
        self.current_yolo_path = yolo_path
        self.current_image_path = image_path
        self.canvas.set_image(image_path, annotations, self.class_names())
        self.labelme_dirty = False
        self.yolo_dirty = self._yolo_needs_save(yolo_path, annotations)
        self._sync_dirty_flag()
        self.refresh_annotation_list()
        self._update_current_file_list_item()
        self._refresh_manual_action_buttons()

    def save_current(
        self,
        *,
        force: bool = False,
        save_json: bool = True,
        save_yolo: bool | None = None,
    ) -> bool:
        should_save_yolo = (
            bool(save_yolo)
            if save_yolo is not None
            else (self.annotation_settings().auto_convert_yolo or force)
        )
        should_save_yolo = should_save_yolo and self.output_mode in {"detect", "obb", "seg"}
        if not self.dirty and not force and not should_save_yolo:
            return False
        if self.current_json_path is None or self.current_image_path is None:
            return False
        if self.canvas.image_size == (0, 0):
            return False
        saved_any = False
        if save_json:
            save_labelme_annotations(
                self.canvas.image_size,
                self.current_json_path,
                self.current_image_path,
                self.canvas.annotations,
                self.class_names(),
            )
            saved_any = True
        if should_save_yolo and self.current_yolo_path is not None:
            save_editable_annotations(
                self.canvas.image_size,
                self.current_yolo_path,
                self.canvas.annotations,
                self.output_mode,
            )
            saved_any = True
        if save_json:
            self.labelme_dirty = False
        if should_save_yolo:
            self.yolo_dirty = False
        self._sync_dirty_flag()
        self._update_current_file_list_item()
        self._refresh_manual_action_buttons()
        return saved_any

    def mark_dirty_and_save(self) -> None:
        self.labelme_dirty = True
        if self.output_mode in {"detect", "obb", "seg"}:
            self.yolo_dirty = True
        self._sync_dirty_flag()
        sync_target_type = getattr(self, "_sync_target_type_to_selection", None)
        if callable(sync_target_type):
            sync_target_type()
        self.refresh_annotation_list()
        annotation_settings = self.annotation_settings()
        self._update_current_file_list_item()
        self._refresh_manual_action_buttons()
        if annotation_settings.auto_save or (
            annotation_settings.auto_convert_yolo and self.output_mode
        ):
            self.save_current(
                save_json=annotation_settings.auto_save,
                save_yolo=annotation_settings.auto_convert_yolo and bool(self.output_mode),
            )

    def _annotation_file_paths(self, image_path: Path) -> tuple[Path, Path]:
        return (
            self.path_from_setting("annotations_dir") / f"{image_path.stem}.json",
            self.path_from_setting("labels_dir") / f"{image_path.stem}.txt",
        )

    def _remove_annotation_files(self, image_path: Path) -> None:
        json_path, yolo_path = self._annotation_file_paths(image_path)
        if json_path.exists():
            json_path.unlink()
        if yolo_path.exists():
            yolo_path.unlink()
