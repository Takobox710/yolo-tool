from __future__ import annotations

import threading
from pathlib import Path
from typing import TYPE_CHECKING

from scr.services.annotation_ai_service import (
    available_ai_models,
    collect_ai_target_images,
    resolve_ai_model_path,
)
from scr.services.detection_service import find_result_model_paths
from scr.services.path_service import simplified_model_path
from scr.ui.qt import (
    QButtonGroup,
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
    QSizePolicy,
    QTableWidget,
    QTextEdit,
    QVBoxLayout,
)
from scr.ui.views.annotation_ai_image_dialog import CustomAiImageSelectionDialog
from scr.ui.views.annotation_ai_mapping import (
    collect_mapping as collect_ai_mapping,
    configure_mapping_table,
    populate_mapping_table as populate_ai_mapping_table,
    update_mapping_status as update_ai_mapping_status,
)
from scr.ui.views.annotation_ai_preferences import (
    ai_prelabel_settings,
    load_ai_prelabel_preferences,
    preferred_ai_model_text,
    save_ai_prelabel_preferences,
)
from scr.ui.workers import AnnotationAiWorker, ModelLabelsWorker

if TYPE_CHECKING:
    from scr.ui.views.annotation import AnnotationPage


class AiPrelabelDialog(QDialog):
    def __init__(self, page: "AnnotationPage", parent=None):
        super().__init__(parent or page)
        self.page = page
        self.stop_event = threading.Event()
        self.ai_worker: AnnotationAiWorker | None = None
        self.labels_worker: ModelLabelsWorker | None = None
        self._model_display_paths: dict[str, Path] = {}
        self.model_labels: list[str] = []
        self.mapping_combos: list[QComboBox] = []
        self.backups: dict[Path, tuple[str | None, str | None]] = {}
        self.custom_selected_images: list[Path] = []
        self.original_class_names = list(page.class_names())
        self._load_saved_preferences()
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
        preferred_model = self._preferred_model_text()
        self.refresh_model_choices(str(preferred_model) if preferred_model else "")
        model_row.addWidget(self.model_combo, 1)
        browse_btn = QPushButton("浏览")
        browse_btn.clicked.connect(self.choose_model)
        model_row.addWidget(browse_btn)
        model_layout.addLayout(model_row)

        threshold_row = QHBoxLayout()
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
        model_layout.addLayout(threshold_row)
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
        if not self.model_labels and self.labels_worker is None:
            self.reload_model_labels()

    def _ai_prelabel_settings(self) -> dict:
        return ai_prelabel_settings(self.page)

    def _load_saved_preferences(self) -> None:
        preferences = load_ai_prelabel_preferences(self.page)
        self.saved_model_path = str(preferences["model_path"])
        self.saved_confidence = float(preferences["confidence"])
        self.saved_iou = float(preferences["iou"])
        self.saved_range_mode = str(preferences["range_mode"])
        self.saved_process_mode = str(preferences["process_mode"])
        self.custom_selected_images = list(preferences["custom_selected_images"])

    def _preferred_model_text(self) -> str:
        return preferred_ai_model_text(self.page, self.saved_model_path)

    def _save_preferences(self) -> None:
        save_ai_prelabel_preferences(
            self.page,
            model_path=self.resolved_model_path(),
            fallback_model_text=self.model_combo.currentText().strip(),
            confidence=float(self.conf_spin.value()),
            iou=float(self.iou_spin.value()),
            range_mode=self.current_range_mode(),
            process_mode=self.current_process_mode(),
            custom_selected_images=self.custom_selected_images,
        )

    def accept(self) -> None:
        self._save_preferences()
        self._stop_ai_worker()
        self._stop_labels_worker()
        super().accept()

    def reject(self) -> None:
        self._save_preferences()
        self._stop_ai_worker()
        self._stop_labels_worker()
        super().reject()

    def closeEvent(self, event):  # noqa: N802 - Qt API name
        self._stop_ai_worker()
        self._stop_labels_worker()
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
            self.model_combo.setCurrentText(self.page.display_path(path))

    def refresh_model_choices(self, preferred_model: str = "") -> None:
        project_root = self.page.project_root()
        result_dir = Path(self.page.app.settings["paths"]["result_dir"])
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

        for model_name in available_ai_models(project_root):
            resolved_text = resolve_ai_model_path(model_name, project_root)
            if resolved_text in seen:
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
        self.mapping_summary.setText("正在加载模型类别...")
        self.mapping_table.setRowCount(0)
        if self.labels_worker is not None and self.labels_worker.isRunning():
            return
        if not model_path:
            self.mapping_summary.setText("未选择模型")
            return
        model_file = Path(model_path)
        if not model_file.exists() or model_file.stat().st_size < 1024:
            self.mapping_summary.setText("模型类别待加载")
            return
        self.labels_worker = ModelLabelsWorker(model_path)
        self.labels_worker.finished_with_labels.connect(self.apply_model_labels)
        self.labels_worker.failed.connect(self.apply_model_labels_error)
        self.labels_worker.finished.connect(self._clear_labels_worker)
        self.labels_worker.start()

    def _clear_labels_worker(self) -> None:
        self.labels_worker = None

    def _stop_labels_worker(self) -> None:
        if self.labels_worker is not None and self.labels_worker.isRunning():
            self.labels_worker.requestInterruption()
            self.labels_worker.quit()
            self.labels_worker.wait(3000)
        self.labels_worker = None

    def apply_model_labels(self, labels: list[str]) -> None:
        self.model_labels = list(labels)
        self.populate_mapping_table()

    def apply_model_labels_error(self, message: str) -> None:
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
        if self.ai_worker is not None and self.ai_worker.isRunning():
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
        mapping = self.collect_mapping()
        if not mapping:
            QMessageBox.warning(self, "AI 预标注", "请至少匹配一个模型类别到标注类别。")
            return
        self._snapshot_targets(targets)
        self.original_class_names = list(self.page.class_names())
        self.progress_bar.setValue(0)
        self.progress_log.clear()
        self.append_log(f"已加载 {len(self.model_labels)} 个模型类别")
        self.stop_event.clear()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.undo_btn.setEnabled(False)
        worker_kwargs = {
            "image_items": [str(path) for path in self.page.image_items],
            "current_image": (
                str(self.page.current_image_path)
                if self.page.current_image_path is not None
                else ""
            ),
            "annotations_dir": str(self.page.path_from_setting("annotations_dir")),
            "labels_dir": str(self.page.path_from_setting("labels_dir")),
            "model_path": model_path,
            "confidence": float(self.conf_spin.value()),
            "iou": float(self.iou_spin.value()),
            "imgsz": max(640, int(self.page.canvas.image_size[0] or 640)),
            "range_mode": self.current_range_mode(),
            "current_index": self.page.current_index,
            "selected_images": [str(path) for path in self.custom_selected_images],
            "process_mode": self.current_process_mode(),
            "class_mapping": mapping,
            "class_names": list(self.page.class_names()),
            "line_expand_pixels": self.page.app.settings.get("annotation", {}).get("line_expand_pixels", 10),
            "output_mode": self.page.output_mode,
            "auto_convert_yolo": bool(self.page.app.settings.get("annotation", {}).get("auto_convert_yolo", False)),
        }
        self.ai_worker = AnnotationAiWorker(worker_kwargs, self.stop_event)
        self.ai_worker.progress_payload.connect(self.apply_progress)
        self.ai_worker.finished_with_result.connect(self.finish_ai_labeling)
        self.ai_worker.failed.connect(self.fail_ai_labeling)
        self.ai_worker.finished.connect(self._clear_ai_worker)
        self.ai_worker.start()

    def _clear_ai_worker(self) -> None:
        self.ai_worker = None

    def _stop_ai_worker(self) -> None:
        if self.ai_worker is None:
            return
        request_stop = getattr(self.ai_worker, "request_stop", None)
        if callable(request_stop):
            request_stop()
        self.ai_worker.wait(3000)
        self.ai_worker = None

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

    def finish_ai_labeling(self, result) -> None:
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        if self.stop_event.is_set():
            self.undo_btn.setEnabled(False)
            self.progress_bar.setValue(0)
            self.append_log("AI 预标注已停止")
            self.stop_event.clear()
            return
        self.undo_btn.setEnabled(bool(self.backups))
        self.progress_bar.setValue(100 if result.total else 0)
        self.append_log(f"完成：已处理 {result.processed}/{result.total} 张图片")
        self.page.refresh_file_list()
        if self.page.current_index >= 0:
            self.page.load_current()

    def fail_ai_labeling(self, message: str) -> None:
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.stop_event.clear()
        self.append_log(f"失败：{message}")
        QMessageBox.warning(self, "AI 预标注", message)

    def stop_ai_labeling(self) -> None:
        self.stop_event.set()
        self.stop_btn.setEnabled(False)
        if self.ai_worker is not None:
            request_stop = getattr(self.ai_worker, "request_stop", None)
            if callable(request_stop):
                request_stop()
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
        self.page.app.settings.setdefault("dataset", {})["class_names"] = list(self.original_class_names)
        self.page.save_settings()
        self.page._refresh_class_state()
        self.page.refresh_file_list()
        if self.page.current_index >= 0:
            self.page.load_current()
        self.append_log("已恢复本次 AI 预标注前的标注文件")
        self.undo_btn.setEnabled(False)
