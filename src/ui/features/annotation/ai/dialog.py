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
from src.ui.shared.workers.ai_runtime import AiRuntimeWorker

if TYPE_CHECKING:
    from src.ui.features.annotation.page import AnnotationPage


class AiPrelabelDialog(QDialog):
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

    def showEvent(self, event):  # noqa: N802 - Qt API name
        super().showEvent(event)
        if not self.model_labels:
            self.reload_model_labels()

    def _ai_prelabel_settings(self) -> dict:
        return ai_prelabel_settings(self.page)

    def _load_saved_preferences(self) -> None:
        preferences = load_ai_prelabel_preferences(self.page)
        self.saved_model_path = str(preferences["model_path"])
        self.saved_confidence = float(preferences["confidence"])
        self.saved_iou = float(preferences["iou"])
        self.saved_sam3_confidence = float(preferences["sam3_confidence"])
        self.saved_sam3_dedup_iou = float(preferences["sam3_dedup_iou"])
        self.saved_sam3_output_shape = str(preferences["sam3_output_shape"])
        self.saved_sam3_prompts = dict(preferences["sam3_prompts"])
        self.saved_sam3_enabled_classes = list(preferences["sam3_enabled_classes"])
        if not self.saved_sam3_prompts and not self.saved_sam3_enabled_classes:
            if str(self.page.output_mode).strip() == "obb":
                self.saved_sam3_output_shape = "obb"
        self.saved_sam3_min_area = int(preferences["sam3_min_area"])
        self.saved_sam3_polygon_simplify_ratio = float(
            preferences["sam3_polygon_simplify_ratio"]
        )
        self.saved_range_mode = str(preferences["range_mode"])
        self.saved_process_mode = str(preferences["process_mode"])
        self.custom_selected_images = list(preferences["custom_selected_images"])

    def _preferred_model_text(self) -> str:
        return preferred_ai_model_text(self.page, self.saved_model_path)

    def _save_preferences(self) -> None:
        self._capture_backend_values()
        prompts, enabled = self.collect_sam3_prompts()
        save_ai_prelabel_preferences(
            self.page,
            model_path=self.resolved_model_path(),
            fallback_model_text=self.model_combo.currentText().strip(),
            confidence=self.saved_confidence,
            iou=self.saved_iou,
            sam3_confidence=self.saved_sam3_confidence,
            sam3_dedup_iou=self.saved_sam3_dedup_iou,
            sam3_output_shape=self.saved_sam3_output_shape,
            sam3_prompts=prompts,
            sam3_enabled_classes=enabled,
            sam3_min_area=self.saved_sam3_min_area,
            sam3_polygon_simplify_ratio=self.saved_sam3_polygon_simplify_ratio,
            range_mode=self.current_range_mode(),
            process_mode=self.current_process_mode(),
            custom_selected_images=self.custom_selected_images,
        )

    def accept(self) -> None:
        self._save_preferences()
        self._shutdown_runtime_worker()
        super().accept()

    def reject(self) -> None:
        self._save_preferences()
        self._shutdown_runtime_worker()
        super().reject()

    def closeEvent(self, event):  # noqa: N802 - Qt API name
        self._save_preferences()
        self._shutdown_runtime_worker()
        super().closeEvent(event)

    def choose_model(self) -> None:
        models_dir = self.page.project_root() / "data" / "models"
        models_dir.mkdir(parents=True, exist_ok=True)
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择模型文件",
            str(models_dir),
            "PyTorch 模型 (*.pt);;所有文件 (*)",
        )
        if path:
            display_name = (
                Path(path).name if is_sam3_checkpoint(path) else self.page.display_path(path)
            )
            self.model_combo.setCurrentText(display_name)

    def refresh_model_choices(self, preferred_model: str = "") -> None:
        project_root = self.page.project_root()
        result_dir = Path(self.page.context.settings.paths.result_dir)
        self._model_display_paths = {}
        display_names: list[str] = []
        seen: set[str] = set()

        for path in find_result_model_paths(
            result_dir, show_last_training_models=False
        ):
            resolved_path = path.resolve()
            resolved_text = str(resolved_path)
            if resolved_text in seen:
                continue
            display_name = simplified_model_path(str(resolved_path), project_root)
            self._model_display_paths[display_name] = resolved_path
            display_names.append(display_name)
            seen.add(resolved_text)

        for path in find_sam3_model_paths(project_root):
            resolved_path = path.resolve()
            resolved_text = str(resolved_path)
            if resolved_text in seen:
                continue
            display_name = resolved_path.name
            self._model_display_paths[display_name] = resolved_path
            display_names.append(display_name)
            seen.add(resolved_text)

        for model_name in available_ai_models(project_root):
            resolved_text = resolve_ai_model_path(model_name, project_root)
            if resolved_text in seen:
                continue
            if Path(resolved_text).name.lower().startswith("sam2"):
                continue
            display_names.append(model_name)
            if resolved_text:
                self._model_display_paths[model_name] = Path(resolved_text)
                seen.add(resolved_text)

        selected_text = ""
        preferred_text = str(preferred_model or "").strip()
        if preferred_text:
            preferred_path = Path(resolve_ai_model_path(preferred_text, project_root))
            for display_name, resolved_path in self._model_display_paths.items():
                if resolved_path == preferred_path:
                    selected_text = display_name
                    break
            else:
                selected_text = preferred_path.name if preferred_path.name else preferred_text

        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        self.model_combo.addItems(display_names)
        if selected_text:
            self.model_combo.setCurrentText(selected_text)
        self.model_combo.blockSignals(False)

    def current_range_mode(self) -> str:
        return self.range_combo.currentText() or "当前图片"

    def current_process_mode(self) -> str:
        return "替换" if self.replace_radio.isChecked() else "追加"

    def resolved_target_images(self) -> list[Path]:
        return collect_ai_target_images(
            self.page.image_items,
            self.page.current_image_path,
            self.page.path_from_setting("annotations_dir"),
            self.page.path_from_setting("labels_dir"),
            self.current_range_mode(),
            current_index=self.page.current_index,
            selected_images=self.custom_selected_images,
        )

    def on_range_mode_changed(self, _text: str = "") -> None:
        is_custom = self.current_range_mode() == "自定义图片"
        self.range_count_label.setHidden(is_custom)
        self.range_list_btn.setHidden(not is_custom)
        self.range_list_btn.setText("列表")
        self.update_target_count()

    def open_custom_image_list(self) -> None:
        if not self.page.image_items:
            QMessageBox.information(self, "AI 预标注", "当前图片文件夹没有可选择的图片。")
            return
        dialog = CustomAiImageSelectionDialog(
            self.page.image_items,
            self.custom_selected_images,
            self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.custom_selected_images = dialog.selected_image_paths()
            self.update_target_count()

    def resolved_model_path(self) -> str:
        text = self.model_combo.currentText().strip()
        mapped = self._model_display_paths.get(text)
        if mapped is not None:
            return str(mapped)
        return resolve_ai_model_path(text, self.page.project_root())

    def reload_model_labels(self) -> None:
        model_path = self.resolved_model_path()
        self._pending_labels_model_path = model_path
        self.model_labels = []
        backend = "sam3" if is_sam3_checkpoint(model_path) else "yolo"
        self._set_backend_controls(backend)
        self.mapping_table.setRowCount(0)
        if not model_path:
            self.mapping_summary.setText("未选择模型")
            return
        if backend == "sam3":
            self.mapping_summary.setText("正在准备 SAM 3 文本提示词")
            self.populate_sam3_prompts()
            return
        configure_mapping_table(self.mapping_table)
        model_file = Path(model_path)
        if not model_file.exists() or model_file.stat().st_size < 1024:
            self.mapping_summary.setText("模型类别待加载")
            return
        self._ensure_runtime_worker_started()
        self.runtime_worker.request_model_labels(model_path)

    def _ensure_runtime_worker_started(self) -> None:
        if not self.runtime_worker.isRunning():
            self.runtime_worker.start()

    def _shutdown_runtime_worker(self) -> None:
        if self.runtime_worker.isRunning():
            self.runtime_worker.shutdown()
            self.runtime_worker.wait(3000)
        self._pending_labels_model_path = ""

    def apply_model_labels(self, model_path: str, labels: list[str]) -> None:
        if str(model_path) != self.resolved_model_path():
            return
        self.model_labels = list(labels)
        self.populate_mapping_table()

    def populate_sam3_prompts(self) -> None:
        self.sam3_class_names = list(self.page.class_names())
        configure_sam3_prompt_table(self.mapping_table)
        self.sam3_checks, self.sam3_prompt_edits = populate_sam3_prompt_table(
            table=self.mapping_table,
            summary=self.mapping_summary,
            class_names=self.sam3_class_names,
            saved_prompts=self.saved_sam3_prompts,
            saved_enabled_classes=self.saved_sam3_enabled_classes,
        )
        for check, edit in zip(self.sam3_checks, self.sam3_prompt_edits):
            check.stateChanged.connect(self.update_sam3_prompt_status)
            edit.textChanged.connect(self.update_sam3_prompt_status)

    def update_sam3_prompt_status(self, *_args) -> None:
        update_sam3_prompt_status(
            self.mapping_table,
            self.mapping_summary,
            self.sam3_checks,
            self.sam3_prompt_edits,
        )

    def collect_sam3_prompts(self) -> tuple[dict[str, str], list[str]]:
        prompts: dict[str, str] = {}
        enabled: list[str] = []
        for name, check, edit in zip(
            self.sam3_class_names,
            self.sam3_checks,
            self.sam3_prompt_edits,
        ):
            prompts[name] = edit.text().strip()
            if check.isChecked():
                enabled.append(name)
        return prompts, enabled

    def _capture_backend_values(self) -> None:
        if self.active_backend == "sam3":
            self.saved_sam3_confidence = float(self.conf_spin.value())
            self.saved_sam3_dedup_iou = float(self.iou_spin.value())
            self.saved_sam3_output_shape = str(self.shape_combo.currentData() or "rect")
            self.saved_sam3_min_area = int(self.sam3_min_area_spin.value())
            self.saved_sam3_polygon_simplify_ratio = self.sam3_simplify_spin.value() / 100.0
        else:
            self.saved_confidence = float(self.conf_spin.value())
            self.saved_iou = float(self.iou_spin.value())

    def _set_backend_controls(self, backend: str) -> None:
        backend = "sam3" if backend == "sam3" else "yolo"
        if backend == self.active_backend:
            if backend == "sam3" and self.sam3_class_names == []:
                self._on_sam3_shape_changed()
            return
        self._capture_backend_values()
        self.active_backend = backend
        if backend == "sam3":
            self.conf_spin.setValue(self.saved_sam3_confidence)
            self.iou_spin.setValue(self.saved_sam3_dedup_iou)
            index = self.shape_combo.findData(self.saved_sam3_output_shape)
            self.shape_combo.setCurrentIndex(max(0, index))
            self.sam3_min_area_spin.setValue(self.saved_sam3_min_area)
            self.sam3_simplify_spin.setValue(self.saved_sam3_polygon_simplify_ratio * 100.0)
            self.conf_spin.setToolTip("SAM 3 概念分割置信度阈值")
            self.iou_spin.setToolTip("不同文本类别结果的 mask 去重阈值")
            self.threshold_widget.setVisible(False)
            self.shape_label.setVisible(True)
            self.shape_combo.setVisible(True)
            self.sam3_advanced_toggle.setVisible(True)
            self.shape_label.setText("标注形状:")
        else:
            self.conf_spin.setValue(self.saved_confidence)
            self.iou_spin.setValue(self.saved_iou)
            self.conf_spin.setToolTip("YOLO 置信度阈值")
            self.iou_spin.setToolTip("YOLO NMS IoU 阈值")
            self.threshold_widget.setVisible(True)
            self.sam3_advanced_toggle.setVisible(False)
            self.sam3_advanced_frame.setVisible(False)
            self.shape_label.setVisible(False)
            self.shape_combo.setVisible(False)

    def _on_sam3_shape_changed(self, *_args) -> None:
        if self.active_backend == "sam3":
            self.saved_sam3_output_shape = str(self.shape_combo.currentData() or "rect")

    def _toggle_sam3_advanced(self, expanded: bool) -> None:
        self.sam3_advanced_toggle.setArrowType(
            Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow
        )
        self.sam3_advanced_frame.setVisible(bool(expanded and self.active_backend == "sam3"))

    def apply_model_labels_error(self, model_path: str, message: str) -> None:
        if str(model_path) != self.resolved_model_path():
            return
        self.mapping_summary.setText(f"加载模型类别失败：{message}")

    def populate_mapping_table(self) -> None:
        self.mapping_combos = populate_ai_mapping_table(
            table=self.mapping_table,
            summary=self.mapping_summary,
            model_labels=self.model_labels,
            class_names=self.page.class_names(),
            status_changed=self.update_mapping_status,
        )

    def update_mapping_status(self) -> None:
        update_ai_mapping_status(
            table=self.mapping_table,
            summary=self.mapping_summary,
            model_labels=self.model_labels,
            mapping_combos=self.mapping_combos,
        )

    def update_target_count(self) -> None:
        targets = self.resolved_target_images()
        if self.current_range_mode() == "自定义图片":
            self.range_list_btn.setText("列表")
            self.range_list_btn.setToolTip(f"当前已选择 {len(targets)} 张图片")
            return
        self.range_count_label.setText(f"已选择 {len(targets)} 张图片")

    def append_log(self, text: str) -> None:
        self.progress_log.append(text)

    def _snapshot_targets(self, targets: list[Path]) -> None:
        self.backups = {}
        for image_path in targets:
            json_path = self.page.path_from_setting("annotations_dir") / f"{image_path.stem}.json"
            yolo_path = self.page.path_from_setting("labels_dir") / f"{image_path.stem}.txt"
            json_text = json_path.read_text(encoding="utf-8") if json_path.exists() else None
            yolo_text = yolo_path.read_text(encoding="utf-8") if yolo_path.exists() else None
            self.backups[image_path] = (json_text, yolo_text)

    def collect_mapping(self) -> dict[str, str]:
        return collect_ai_mapping(self.mapping_table, self.mapping_combos)

    def start_ai_labeling(self) -> None:
        if not self.start_btn.isEnabled():
            return
        if self.page.context.tasks.is_active("ai_label"):
            QMessageBox.information(self, "AI 预标注", "已有 AI 预标注任务正在运行。")
            return
        model_path = self.resolved_model_path()
        if not model_path:
            QMessageBox.warning(self, "AI 预标注", "请先选择模型文件。")
            return
        targets = self.resolved_target_images()
        if self.current_range_mode() == "自定义图片" and not targets:
            QMessageBox.information(self, "AI 预标注", "请先在图片列表中勾选至少一张图片。")
            return
        if not targets:
            QMessageBox.information(self, "AI 预标注", "当前没有可处理的图片。")
            return
        self._capture_backend_values()
        sam3_prompts, sam3_enabled = self.collect_sam3_prompts()
        if self.active_backend == "sam3":
            valid_prompts = [
                name for name in sam3_enabled if sam3_prompts.get(name, "").strip()
            ]
            if not valid_prompts:
                QMessageBox.warning(self, "AI 预标注", "请至少启用一个带文本提示词的项目类别。")
                return
            mapping = {}
        else:
            mapping = self.collect_mapping()
            if not mapping:
                QMessageBox.warning(self, "AI 预标注", "请至少匹配一个模型类别到标注类别。")
                return
        self.page.sam_assist.release_for_ai_prelabel()
        self._snapshot_targets(targets)
        self.original_class_names = list(self.page.class_names())
        self.progress_bar.setValue(0)
        self.progress_log.clear()
        if self.active_backend == "sam3":
            self.append_log(f"已启用 {len(valid_prompts)} 个 SAM 3 文本提示词")
        else:
            self.append_log(f"已加载 {len(self.model_labels)} 个模型类别")
        self.stop_event.clear()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.undo_btn.setEnabled(False)
        self._ai_lease = self.page.context.tasks.begin(
            "ai_label",
            generation=self.page.context.generation,
            stop=self.runtime_worker.request_stop,
        )
        if self._ai_lease is None:
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            return
        worker_kwargs = {
            "image_items": [str(path) for path in self.page.image_items],
            "target_images": [str(path) for path in targets],
            "current_image": (
                str(self.page.current_image_path)
                if self.page.current_image_path is not None
                else ""
            ),
            "annotations_dir": str(self.page.path_from_setting("annotations_dir")),
            "labels_dir": str(self.page.path_from_setting("labels_dir")),
            "model_path": model_path,
            "backend": self.active_backend,
            "confidence": float(self.conf_spin.value()),
            "iou": float(self.iou_spin.value()),
            "imgsz": max(640, int(self.page.canvas.image_size[0] or 640)),
            "range_mode": self.current_range_mode(),
            "current_index": self.page.current_index,
            "selected_images": [str(path) for path in self.custom_selected_images],
            "process_mode": self.current_process_mode(),
            "class_mapping": mapping,
            "class_names": list(self.page.class_names()),
            "sam3_prompts": sam3_prompts,
            "sam3_enabled_classes": sam3_enabled,
            "sam3_output_shape": self.saved_sam3_output_shape,
            "sam3_min_area": self.saved_sam3_min_area,
            "sam3_polygon_simplify_ratio": self.saved_sam3_polygon_simplify_ratio,
            "line_expand_pixels": self.page.context.settings.annotation.line_expand_pixels,
            "output_mode": self.page.output_mode,
            "auto_convert_yolo": bool(self.page.context.settings.annotation.auto_convert_yolo),
        }
        self._ensure_runtime_worker_started()
        self.runtime_worker.start_ai_labeling(worker_kwargs)

    def apply_progress(self, payload: dict) -> None:
        total = max(1, int(payload.get("total") or 1))
        index = int(payload.get("index") or 0)
        self.progress_bar.setValue(int(index * 100 / total))
        if payload.get("type") == "log":
            self.append_log(str(payload.get("message") or ""))
            return
        image_name = str(payload.get("image_name") or "")
        result_count = int(payload.get("result_count") or 0)
        self.append_log(f"{index}/{total} {image_name} -> 新增 {result_count} 个标注")
        stats = dict(payload.get("sam3_stats") or {})
        if stats:
            self.append_log(
                f"  SAM 3 候选 {stats.get('raw_count', 0)}，"
                f"面积过滤 {stats.get('area_filtered', 0)}，"
                f"重叠去重 {stats.get('overlap_filtered', 0)}"
            )

    def finish_ai_labeling(self, result) -> None:
        if not self.page.context.tasks.is_current(self._ai_lease):
            return
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        if self.stop_event.is_set():
            self.undo_btn.setEnabled(bool(self.backups))
            self.progress_bar.setValue(0)
            self.append_log("AI 预标注已停止")
            self.stop_event.clear()
            self.page.context.tasks.finish(self._ai_lease)
            self._ai_lease = None
            return
        self.undo_btn.setEnabled(bool(self.backups))
        self.progress_bar.setValue(100 if result.total else 0)
        self.append_log(f"完成：已处理 {result.processed}/{result.total} 张图片")
        self.page.refresh_file_list()
        if self.page.current_index >= 0:
            self.page.load_current()
        self.page.context.tasks.finish(self._ai_lease)
        self._ai_lease = None

    def fail_ai_labeling(self, message: str) -> None:
        if not self.page.context.tasks.is_current(self._ai_lease):
            return
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.undo_btn.setEnabled(bool(self.backups))
        self.stop_event.clear()
        self.page.context.tasks.finish(self._ai_lease)
        self._ai_lease = None
        self.append_log(f"失败：{message}")
        QMessageBox.warning(self, "AI 预标注", message)

    def stop_ai_labeling(self) -> None:
        self.stop_event.set()
        self.stop_btn.setEnabled(False)
        self.runtime_worker.request_stop()
        self.append_log("已请求停止 AI 预标注")

    def undo_ai_changes(self) -> None:
        if not self.backups:
            return
        for image_path, (json_text, yolo_text) in self.backups.items():
            json_path = self.page.path_from_setting("annotations_dir") / f"{image_path.stem}.json"
            yolo_path = self.page.path_from_setting("labels_dir") / f"{image_path.stem}.txt"
            if json_text is None:
                if json_path.exists():
                    json_path.unlink()
            else:
                json_path.write_text(json_text, encoding="utf-8")
            if yolo_text is None:
                if yolo_path.exists():
                    yolo_path.unlink()
            else:
                yolo_path.write_text(yolo_text, encoding="utf-8")
        self.page.context.settings.dataset.class_names = list(self.original_class_names)
        self.page.save_settings()
        self.page._refresh_class_state()
        self.page.refresh_file_list()
        if self.page.current_index >= 0:
            self.page.load_current()
        self.append_log("已恢复本次 AI 预标注前的标注文件")
        self.undo_btn.setEnabled(False)
