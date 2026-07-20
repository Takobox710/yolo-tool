from __future__ import annotations

from pathlib import Path

from src.services.annotation import (
    EditableAnnotation,
    load_editable_annotations,
    load_labelme_annotations,
    save_editable_annotations,
    save_labelme_annotations,
)
from src.ui.shared.page_base import BasePage
from src.shared.qt import (
    QAbstractItemView,
    QEvent,
    QFileDialog,
    QHBoxLayout,
    QListWidgetItem,
    QMessageBox,
    Qt,
    QTimer,
)
from src.ui.features.annotation.actions import AnnotationActionsMixin
from src.ui.features.annotation.ai.dialog import AiPrelabelDialog, CustomAiImageSelectionDialog
from src.ui.features.annotation.canvas.widget import AnnotationCanvas
from src.ui.features.annotation.class_panel import AnnotationClassPanelMixin
from src.ui.features.annotation.dialogs import AnnotationSettingsDialog, ClassManagerDialog, DrawShapeDialog
from src.ui.features.annotation.file_browser import AnnotationFileBrowserMixin
from src.ui.features.annotation.layout import build_center, build_right_panel
from src.ui.features.annotation.menus import AnnotationMenuMixin
from src.ui.features.annotation.persistence import AnnotationPersistenceMixin
from src.ui.features.annotation.selection import AnnotationSelectionMixin
from src.ui.features.annotation.settings_actions import AnnotationPageSettingsMixin
from src.ui.features.annotation.shortcuts import register_annotation_shortcuts
from src.ui.features.annotation.toolbar import build_toolbar
from src.ui.shared.workers import Worker


class AnnotationPage(
    AnnotationActionsMixin,
    AnnotationClassPanelMixin,
    AnnotationFileBrowserMixin,
    AnnotationMenuMixin,
    AnnotationPersistenceMixin,
    AnnotationPageSettingsMixin,
    AnnotationSelectionMixin,
    BasePage,
):
    def __init__(self, app):
        super().__init__(app)
        self.image_items: list[Path] = []
        self.current_index = -1
        self.dirty = False
        self.current_json_path: Path | None = None
        self.current_yolo_path: Path | None = None
        self.current_image_path: Path | None = None
        self.output_mode = self.app.settings.get("task", {}).get("mode", "detect")
        self.current_class_id = 0
        self._annotation_statuses: dict[str, bool] = {}
        self._file_list_rendered_count = 0
        self._file_list_batch_size = 20
        self._annotation_status_request_id = 0
        self._annotation_status_worker: Worker | None = None
        self._initialized_once = False
        self._file_list_render_timer = QTimer(self)
        self._file_list_render_timer.setInterval(16)
        self._file_list_render_timer.timeout.connect(self._render_next_file_list_batch)

        root = QHBoxLayout(self)
        root.setContentsMargins(20, 14, 12, 12)
        root.setSpacing(8)
        root.addWidget(build_toolbar(self))
        root.addLayout(build_center(self), 1)
        root.addWidget(build_right_panel(self))

        self._refresh_class_state()
        self._refresh_path_labels()
        register_annotation_shortcuts(self)

    def _list_widget_item_factory(self, text: str | None = None) -> QListWidgetItem:
        return QListWidgetItem("" if text is None else text)

    @staticmethod
    def _custom_context_menu_policy():
        return Qt.ContextMenuPolicy.CustomContextMenu

    def _show_image_open_error(self, exc: OSError) -> None:
        QMessageBox.warning(self, "数据标注", f"无法打开图片：{exc}")

    def choose_image_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "选择图片文件夹", str(self.path_from_setting("images_dir"))
        )
        if not directory:
            return
        self.save_current()
        self.update_setting("paths", "images_dir", value=directory)
        self._refresh_path_labels()
        self.scan_images(select_first=True)

    def choose_label_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "选择 Labelme JSON 标签文件夹", str(self.path_from_setting("annotations_dir"))
        )
        if not directory:
            return
        self.save_current()
        self.update_setting("paths", "annotations_dir", value=directory)
        Path(directory).mkdir(parents=True, exist_ok=True)
        self._refresh_path_labels()
        self.load_current()
        self.refresh_file_list()

    def path_from_setting(self, key: str) -> Path:
        return Path(self.app.settings["paths"][key])

    def annotation_settings(self) -> dict:
        return self.app.settings.get("annotation", {})

    def labelme_auto_save_enabled(self) -> bool:
        return bool(self.annotation_settings().get("auto_save", True))

    def yolo_auto_save_enabled(self) -> bool:
        return bool(self.annotation_settings().get("auto_convert_yolo", False))

    def show_yolo_save_in_context_menu(self) -> bool:
        return bool(self.annotation_settings().get("show_yolo_save_in_context_menu", False))

    def _refresh_path_labels(self) -> None:
        return None

    def on_setting_changed(self, keys, value):
        if keys == ("paths", "images_dir"):
            self.scan_images(select_first=True)
        elif keys == ("paths", "annotations_dir"):
            self.load_current()
            self.refresh_file_list()
        elif keys == ("paths", "labels_dir"):
            self.load_current()
            self.refresh_file_list()

    def change_output_mode(self, text: str) -> None:
        mode = text if text in {"detect", "obb"} else "detect"
        self.output_mode = mode
        self.app.settings.setdefault("task", {})["mode"] = mode
        self.save_settings()
        if self.current_json_path is not None:
            self.dirty = True
            self.save_current()

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

    def has_unsaved_annotations(self) -> bool:
        return bool(self.dirty)

    def eventFilter(self, watched, event):  # noqa: N802 - Qt API name
        if watched is self.file_list.viewport():
            if event.type() in {
                QEvent.Type.Paint,
                QEvent.Type.Resize,
                QEvent.Type.Wheel,
            }:
                decorate_rows = getattr(self, "_decorate_visible_rows", None)
                if callable(decorate_rows):
                    QTimer.singleShot(0, self, decorate_rows)
        return super().eventFilter(watched, event)


__all__ = [
    "AnnotationPage",
    "EditableAnnotation",
    "load_editable_annotations",
    "load_labelme_annotations",
    "save_editable_annotations",
    "save_labelme_annotations",
    "AnnotationCanvas",
    "AnnotationSettingsDialog",
    "DrawShapeDialog",
    "CustomAiImageSelectionDialog",
    "AiPrelabelDialog",
    "ClassManagerDialog",
]
