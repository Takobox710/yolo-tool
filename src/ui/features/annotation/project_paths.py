from __future__ import annotations

from pathlib import Path

from src.shared.qt import QFileDialog, QListWidgetItem, QMessageBox, Qt


class AnnotationProjectPathsMixin:
    def _list_widget_item_factory(self, text: str | None = None) -> QListWidgetItem:
        return QListWidgetItem("" if text is None else text)

    @staticmethod
    def _custom_context_menu_policy():
        return Qt.ContextMenuPolicy.CustomContextMenu

    def _show_image_open_error(self, exc: OSError) -> None:
        QMessageBox.warning(self, "数据标注", f"无法打开图片：{exc}")

    def choose_image_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "选择图片文件夹", str(self.path_from_setting("images_dir")))
        if not directory:
            return
        self.save_current()
        self.clear_annotation_history()
        self.update_setting("paths", "images_dir", value=directory)
        self._refresh_path_labels()
        self.scan_images(select_first=True)

    def choose_label_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "选择 Labelme JSON 标签文件夹", str(self.path_from_setting("annotations_dir")))
        if not directory:
            return
        self.save_current()
        self.clear_annotation_history()
        self.update_setting("paths", "annotations_dir", value=directory)
        Path(directory).mkdir(parents=True, exist_ok=True)
        self._refresh_path_labels()
        self.load_current()
        self.refresh_file_list()

    def path_from_setting(self, key: str) -> Path:
        return Path(getattr(self.context.settings.paths, key))

    def annotation_settings(self):
        return self.context.settings.annotation

    def labelme_auto_save_enabled(self) -> bool:
        return bool(self.annotation_settings().auto_save)

    def yolo_auto_save_enabled(self) -> bool:
        return bool(self.annotation_settings().auto_convert_yolo)

    def load_yolo_when_labelme_missing(self) -> bool:
        return bool(self.annotation_settings().load_yolo_when_labelme_missing)

    def show_yolo_save_in_context_menu(self) -> bool:
        return bool(self.annotation_settings().show_yolo_save_in_context_menu)

    def yolo_features_enabled(self) -> bool:
        return self.yolo_auto_save_enabled() or self.show_yolo_save_in_context_menu()

    def _refresh_path_labels(self) -> None:
        return None


__all__ = ["AnnotationProjectPathsMixin"]
