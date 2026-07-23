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


class AnnotationPersistenceMixin:
    def _sync_project_labelme_class_names(self) -> None:
        names = collect_labelme_class_names(
            self.path_from_setting("annotations_dir"), self.class_names()
        )
        if names == self.class_names():
            return
        self.app.settings.setdefault("dataset", {})["class_names"] = names
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
                self.app.settings.get("annotation", {}).get("line_expand_pixels", 10),
            )
            if class_names != self.class_names():
                self.app.settings.setdefault("dataset", {})["class_names"] = class_names
                self.save_settings()
                self._refresh_class_state()
        else:
            annotations = load_editable_annotations(image_size, yolo_path)
        self.current_json_path = json_path
        self.current_yolo_path = yolo_path
        self.current_image_path = image_path
        self.canvas.set_image(image_path, annotations, self.class_names())
        self.dirty = False
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
            else (self.annotation_settings().get("auto_convert_yolo", False) or force)
        )
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
            self.dirty = False
        self._update_current_file_list_item()
        self._refresh_manual_action_buttons()
        return saved_any

    def mark_dirty_and_save(self) -> None:
        self.dirty = True
        sync_target_type = getattr(self, "_sync_target_type_to_selection", None)
        if callable(sync_target_type):
            sync_target_type()
        self.refresh_annotation_list()
        annotation_settings = self.annotation_settings()
        self._update_current_file_list_item()
        self._refresh_manual_action_buttons()
        if annotation_settings.get("auto_save", True) or annotation_settings.get("auto_convert_yolo", False):
            self.save_current(
                save_json=annotation_settings.get("auto_save", True),
                save_yolo=annotation_settings.get("auto_convert_yolo", False),
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
