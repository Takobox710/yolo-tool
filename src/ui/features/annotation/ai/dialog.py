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

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(10)

        model_card = QFrame()
        model_card.setObjectName("card")
        model_layout = QVBoxLayout(model_card)
        model_layout.setContentsMargins(12, 10, 12, 10)
        model_layout.setSpacing(8)
        title = QLabel("模型与参数")
        title.setObjectName("sectionTitle")
        model_layout.addWidget(title)

        model_row = QHBoxLayout()
        model_row.setContentsMargins(0, 0, 0, 0)
        model_row.setSpacing(8)
        model_label = QLabel("模型文件:")
        model_label.setObjectName("annotationPathLabel")
        model_row.addWidget(model_label)
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.lineEdit().setStyleSheet(
            "QLineEdit { padding: 0; border: 0; background: transparent; }"
        )
        preferred_model = self._preferred_model_text()
        self.refresh_model_choices(str(preferred_model) if preferred_model else "")
        model_row.addWidget(self.model_combo, 1)
        browse_btn = QPushButton("浏览")
        browse_btn.clicked.connect(self.choose_model)
        model_row.addWidget(browse_btn)
        model_layout.addLayout(model_row)

        self.threshold_widget = QWidget()
        threshold_row = QHBoxLayout(self.threshold_widget)
        threshold_row.setContentsMargins(0, 0, 0, 0)
        threshold_row.setSpacing(8)
        conf_label = QLabel("置信度:")
        conf_label.setObjectName("annotationPathLabel")
        threshold_row.addWidget(conf_label)
        self.conf_spin = QDoubleSpinBox()
        self.conf_spin.setRange(0.0, 1.0)
        self.conf_spin.setSingleStep(0.05)
        self.conf_spin.setDecimals(2)
        self.conf_spin.setValue(self.saved_confidence)
        threshold_row.addWidget(self.conf_spin)
        iou_label = QLabel("IoU:")
        iou_label.setObjectName("annotationPathLabel")
        threshold_row.addSpacing(12)
        threshold_row.addWidget(iou_label)
        self.iou_spin = QDoubleSpinBox()
        self.iou_spin.setRange(0.0, 1.0)
        self.iou_spin.setSingleStep(0.05)
        self.iou_spin.setDecimals(2)
        self.iou_spin.setValue(self.saved_iou)
        threshold_row.addWidget(self.iou_spin)
        threshold_row.addStretch(1)
        model_layout.addWidget(self.threshold_widget)

        self.sam3_advanced_toggle = QToolButton()
        self.sam3_advanced_toggle.setText("高级参数")
        self.sam3_advanced_toggle.setCheckable(True)
        self.sam3_advanced_toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.sam3_advanced_toggle.setArrowType(Qt.ArrowType.RightArrow)
        self.sam3_advanced_toggle.toggled.connect(self._toggle_sam3_advanced)

        shape_row = QHBoxLayout()
        shape_row.setContentsMargins(0, 0, 0, 0)
        shape_row.setSpacing(8)
        self.shape_label = QLabel("标注形状:")
        self.shape_label.setObjectName("annotationPathLabel")
        shape_row.addWidget(self.shape_label)
        self.shape_combo = QComboBox()
        self.shape_combo.addItem("矩形框", "rect")
        self.shape_combo.addItem("有向矩形", "obb")
        self.shape_combo.addItem("多边形", "polygon")
        self.shape_combo.currentIndexChanged.connect(self._on_sam3_shape_changed)
        shape_row.addWidget(self.shape_combo, 1)
        shape_row.addWidget(self.sam3_advanced_toggle)
        model_layout.addLayout(shape_row)

        self.sam3_advanced_frame = QFrame()
        advanced_layout = QHBoxLayout(self.sam3_advanced_frame)
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        advanced_layout.setSpacing(8)
        min_area_label = QLabel("最小面积:")
        min_area_label.setObjectName("annotationPathLabel")
        advanced_layout.addWidget(min_area_label)
        self.sam3_min_area_spin = QSpinBox()
        self.sam3_min_area_spin.setRange(1, 100000000)
        self.sam3_min_area_spin.setValue(self.saved_sam3_min_area)
        advanced_layout.addWidget(self.sam3_min_area_spin)
        simplify_label = QLabel("轮廓简化 %:")
        simplify_label.setObjectName("annotationPathLabel")
        advanced_layout.addWidget(simplify_label)
        self.sam3_simplify_spin = QDoubleSpinBox()
        self.sam3_simplify_spin.setRange(0.0, 10.0)
        self.sam3_simplify_spin.setSingleStep(0.1)
        self.sam3_simplify_spin.setDecimals(2)
        self.sam3_simplify_spin.setButtonSymbols(
            QAbstractSpinBox.ButtonSymbols.NoButtons
        )
        self.sam3_simplify_spin.setValue(self.saved_sam3_polygon_simplify_ratio * 100.0)
        advanced_layout.addWidget(self.sam3_simplify_spin)
        advanced_layout.addStretch(1)
        self.sam3_advanced_frame.setVisible(False)
        model_layout.addWidget(self.sam3_advanced_frame)
        top_row.addWidget(model_card, 3)

        options_card = QFrame()
        options_card.setObjectName("card")
        options_layout = QVBoxLayout(options_card)
        options_layout.setContentsMargins(12, 10, 12, 10)
        options_layout.setSpacing(8)
        options_title = QLabel("范围与模式")
        options_title.setObjectName("sectionTitle")
        options_layout.addWidget(options_title)

        range_row = QHBoxLayout()
        range_row.setContentsMargins(0, 0, 0, 0)
        range_row.setSpacing(8)
        range_label = QLabel("标注范围:")
        range_label.setObjectName("annotationPathLabel")
        range_row.addWidget(range_label)
        self.range_combo = QComboBox()
        self.range_combo.addItems(
            ["当前图片", "当前及以后图片", "全部未标注图片", "全部图片", "自定义图片"]
        )
        self.range_combo.currentTextChanged.connect(self.on_range_mode_changed)
        self.range_combo.setCurrentText(self.saved_range_mode)
        range_row.addWidget(self.range_combo, 1)
        self.range_count_label = QLabel("")
        self.range_count_label.setObjectName("fieldLabel")
        range_row.addWidget(self.range_count_label)
        self.range_list_btn = QPushButton("图片列表")
        self.range_list_btn.setObjectName("softButton")
        self.range_list_btn.clicked.connect(self.open_custom_image_list)
        self.range_list_btn.hide()
        range_row.addWidget(self.range_list_btn)
        options_layout.addLayout(range_row)

        process_row = QHBoxLayout()
        process_row.setContentsMargins(0, 0, 0, 0)
        process_row.setSpacing(8)
        process_label = QLabel("处理模式:")
        process_label.setObjectName("annotationPathLabel")
        process_row.addWidget(process_label)
        self.append_radio = QRadioButton("追加")
        self.append_radio.setToolTip("保留原有标注，并追加 AI 识别出的新标注。")
        self.replace_radio = QRadioButton("替换")
        self.replace_radio.setToolTip("清除原有标注，仅保留本次 AI 预标注结果。")
        self.append_radio.setChecked(self.saved_process_mode != "替换")
        self.replace_radio.setChecked(self.saved_process_mode == "替换")
        self.process_group = QButtonGroup(self)
        self.process_group.addButton(self.append_radio)
        self.process_group.addButton(self.replace_radio)
        process_row.addWidget(self.append_radio)
        process_row.addWidget(self.replace_radio)
        process_row.addStretch(1)
        options_layout.addLayout(process_row)
        options_layout.addStretch(1)
        top_row.addWidget(options_card, 2)
        root.addLayout(top_row)

        mapping_card = QFrame()
        mapping_card.setObjectName("card")
        mapping_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        mapping_layout = QVBoxLayout(mapping_card)
        mapping_layout.setContentsMargins(12, 10, 12, 10)
        mapping_layout.setSpacing(6)
        mapping_header = QHBoxLayout()
        mapping_header.setContentsMargins(0, 0, 0, 0)
        mapping_title = QLabel("类别映射")
        mapping_title.setObjectName("sectionTitle")
        mapping_header.addWidget(mapping_title)
        mapping_header.addStretch(1)
        self.mapping_summary = QLabel("等待加载模型类别")
        self.mapping_summary.setObjectName("fieldLabel")
        mapping_header.addWidget(self.mapping_summary)
        mapping_layout.addLayout(mapping_header)
        self.mapping_table = QTableWidget(0, 4)
        configure_mapping_table(self.mapping_table)
        self.mapping_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        mapping_layout.addWidget(self.mapping_table, 1)
        root.addWidget(mapping_card, 4)

        progress_card = QFrame()
        progress_card.setObjectName("card")
        progress_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        progress_layout = QVBoxLayout(progress_card)
        progress_layout.setContentsMargins(12, 10, 12, 10)
        progress_layout.setSpacing(6)
        progress_header = QHBoxLayout()
        progress_header.setContentsMargins(0, 0, 0, 0)
        progress_title = QLabel("运行进度")
        progress_title.setObjectName("sectionTitle")
        progress_header.addWidget(progress_title)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_header.addWidget(self.progress_bar, 1)
        progress_layout.addLayout(progress_header)
        self.progress_log = QTextEdit()
        self.page.prepare_readonly_text(self.progress_log)
        self.progress_log.setMinimumHeight(44)
        self.progress_log.setMaximumHeight(88)
        progress_layout.addWidget(self.progress_log, 1)
        root.addWidget(progress_card)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 2, 0, 0)
        button_row.setSpacing(10)
        button_row.addStretch(1)
        self.start_btn = QPushButton("开始预标注")
        self.start_btn.clicked.connect(self.start_ai_labeling)
        button_row.addWidget(self.start_btn)
        self.stop_btn = QPushButton("停止标注")
        self.stop_btn.setObjectName("softButton")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_ai_labeling)
        button_row.addWidget(self.stop_btn)
        self.undo_btn = QPushButton("删除AI标注")
        self.undo_btn.setEnabled(False)
        self.undo_btn.clicked.connect(self.undo_ai_changes)
        button_row.addWidget(self.undo_btn)
        back_btn = QPushButton("返回标注")
        back_btn.setObjectName("softButton")
        back_btn.clicked.connect(self.accept)
        button_row.addWidget(back_btn)
        root.addLayout(button_row)

        self.model_combo.currentTextChanged.connect(self.reload_model_labels)
        self.on_range_mode_changed(self.current_range_mode())
