from __future__ import annotations

import threading
from pathlib import Path
from typing import TYPE_CHECKING

from src.services.annotation import (
    available_ai_models,
    collect_ai_target_images,
    resolve_ai_model_path,
)
from src.services.annotation.sam3_text import find_sam3_model_paths, is_sam3_checkpoint
from src.services.data_ops import simplified_model_path
from src.services.validation import find_result_model_paths
from src.shared.qt import (
    QAbstractSpinBox,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QSizePolicy,
    QTableWidget,
    QTextEdit,
    QVBoxLayout,
    QToolButton,
    Qt,
    QWidget,
)
from src.ui.features.annotation.ai.image_selection_dialog import CustomAiImageSelectionDialog
from src.ui.features.annotation.ai.mapping import (
    collect_mapping as collect_ai_mapping,
    configure_mapping_table,
    configure_sam3_prompt_table,
    populate_mapping_table as populate_ai_mapping_table,
    populate_sam3_prompt_table,
    update_mapping_status as update_ai_mapping_status,
    update_sam3_prompt_status,
)
from src.ui.features.annotation.ai.preferences import (
    ai_prelabel_settings,
    load_ai_prelabel_preferences,
    preferred_ai_model_text,
    save_ai_prelabel_preferences,
)
from src.ui.features.annotation.ai.prelabel_mapping import AiPrelabelMappingMixin
from src.ui.features.annotation.ai.prelabel_runtime import AiPrelabelRuntimeMixin
from src.ui.features.annotation.ai.prelabel_state import AiPrelabelStateMixin
from src.ui.shared.workers.ai_runtime import AiRuntimeWorker

if TYPE_CHECKING:
    from src.ui.features.annotation.page import AnnotationPage


class AiPrelabelDialog(
    AiPrelabelStateMixin,
    AiPrelabelMappingMixin,
    AiPrelabelRuntimeMixin,
    QDialog,
):
    def __init__(self, page: "AnnotationPage", parent=None):
        super().__init__(parent or page)
        self.page = page
        self.stop_event = threading.Event()
        self._ai_lease = None
        self.runtime_worker = AiRuntimeWorker()
        self._model_display_paths: dict[str, Path] = {}
        self._pending_labels_model_path = ""
        self.model_labels: list[str] = []
        self.mapping_combos: list[QComboBox] = []
        self.sam3_checks: list[QCheckBox] = []
        self.sam3_prompt_edits = []
        self.sam3_class_names: list[str] = []
        self.active_backend = ""
        self.backups: dict[Path, tuple[str | None, str | None]] = {}
        self.custom_selected_images: list[Path] = []
        self.original_class_names = list(page.class_names())
        self._load_saved_preferences()
        self.runtime_worker.model_labels_loaded.connect(self.apply_model_labels)
        self.runtime_worker.model_labels_failed.connect(self.apply_model_labels_error)
        self.runtime_worker.progress_payload.connect(self.apply_progress)
        self.runtime_worker.finished_with_result.connect(self.finish_ai_labeling)
        self.runtime_worker.failed.connect(self.fail_ai_labeling)
        self.setWindowTitle("AI 智能预标注")
        self.resize(700, 620)
        self.setMinimumSize(650, 520)
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 12)
        root.setSpacing(10)
        from src.ui.features.annotation.ai.dialog_model_layout import build_model_card
        from src.ui.features.annotation.ai.dialog_scope_layout import build_scope_card
        from src.ui.features.annotation.ai.dialog_result_layout import build_result_layout
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(10)
        top_row.addWidget(build_model_card(self), 3)
        top_row.addWidget(build_scope_card(self), 2)
        root.addLayout(top_row)
        build_result_layout(self, root)
        self.model_combo.currentTextChanged.connect(self.reload_model_labels)
        self.on_range_mode_changed(self.current_range_mode())
