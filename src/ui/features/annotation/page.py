from __future__ import annotations

from pathlib import Path

from src.services.annotation import (
    EditableAnnotation,
    load_editable_annotations,
    load_labelme_annotations,
    save_editable_annotations,
    save_labelme_annotations,
)
from src.services.annotation.history import AnnotationHistory
from src.ui.shared.page_base import BasePage
from src.shared.qt import QHBoxLayout, QTimer, QVBoxLayout
from src.ui.features.annotation.actions import AnnotationActionsMixin
from src.ui.features.annotation.ai.dialog import AiPrelabelDialog, CustomAiImageSelectionDialog
from src.ui.features.annotation.canvas.widget import AnnotationCanvas
from src.ui.features.annotation.class_panel import AnnotationClassPanelMixin
from src.ui.features.annotation.dialogs import AnnotationSettingsDialog, ClassManagerDialog, DrawShapeDialog
from src.ui.features.annotation.file_browser import AnnotationFileBrowserMixin
from src.ui.features.annotation.lifecycle import AnnotationLifecycleMixin
from src.ui.features.annotation.layout import (
    build_center,
    build_right_panel,
    build_status_bar,
    set_annotation_bottom_margin,
)
from src.ui.features.annotation.menus import AnnotationMenuMixin
from src.ui.features.annotation.persistence import AnnotationPersistenceMixin
from src.ui.features.annotation.selection import AnnotationSelectionMixin
from src.ui.features.annotation.project_paths import AnnotationProjectPathsMixin
from src.ui.features.annotation.settings_actions import AnnotationPageSettingsMixin
from src.ui.features.annotation.shortcuts import register_annotation_shortcuts
from src.ui.features.annotation.sam import SamAssistController
from src.ui.features.annotation.task_mode import AnnotationTaskModeMixin
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
    AnnotationProjectPathsMixin,
    AnnotationTaskModeMixin,
    AnnotationLifecycleMixin,
    BasePage,
):
    def __init__(self, context):
        super().__init__(context)
        self.image_items: list[Path] = []
        self.current_index = -1
        self.dirty = False
        self.annotation_history = AnnotationHistory(limit=5)
        self.current_json_path: Path | None = None
        self.current_yolo_path: Path | None = None
        self.current_image_path: Path | None = None
        self.output_mode = (
            self.context.settings.task.mode
            if self.context.settings.task.mode_selected
            else None
        )
        self.current_class_id = 0
        self.labelme_dirty = False
        self.yolo_dirty = False
        self._mode_probe_signature: tuple[str, str] | None = None
        self._annotation_statuses: dict[str, bool] = {}
        self._file_list_rendered_count = 0
        self._file_list_batch_size = 20
        self._annotation_status_request_id = 0
        self._annotation_status_worker: Worker | None = None
        self._initialized_once = False
        self._file_list_render_timer = QTimer(self)
        self._file_list_render_timer.setInterval(16)
        self._file_list_render_timer.timeout.connect(self._render_next_file_list_batch)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 14, 12, 12)
        root.setSpacing(3)
        self.annotation_root_layout = root
        modules = QHBoxLayout()
        modules.setContentsMargins(0, 0, 0, 0)
        modules.setSpacing(8)
        self.annotation_modules_layout = modules
        modules.addWidget(build_toolbar(self))
        modules.addLayout(build_center(self), 1)
        modules.addWidget(build_right_panel(self))
        root.addLayout(modules, 1)
        root.addWidget(build_status_bar(self))
        self.canvas.status_changed_callback = self.refresh_annotation_status_bar
        self.sam_assist = SamAssistController(self)

        self._refresh_class_state()
        self._refresh_path_labels()
        register_annotation_shortcuts(self)

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
