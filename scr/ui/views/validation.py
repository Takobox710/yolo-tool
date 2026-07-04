from __future__ import annotations

import os
import threading
from pathlib import Path
from queue import Queue

import yaml

from scr.paths import ROOT
from scr.services.detection_service import collect_prediction_sources
from scr.services.runtime_service import spawn_logged_process, stop_process
from scr.services.training_service import build_val_command
from scr.ui.helpers import _build_detection_log_message, _detection_counter_text, _find_models_full_paths, _is_live_source_mode, _should_store_detection_history, _simplified_model_path, _resolve_project_path
from scr.ui.page_base import BasePage, Card, ImageView
from scr.ui.qt import Qt, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QHeaderView, QLabel, QListWidget, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QTextEdit, QTimer, QVBoxLayout, QWidget
from scr.ui.workers import DetectionWorker

SOURCE_SCOPE_OPTIONS = ["全部图片", "训练图片", "验证图片", "测试图片"]


class ValidatePage(BasePage):
    def __init__(self, app):
        super().__init__(app)
        self.detect_results = []
        self.detect_index = -1
        self.detect_stop = threading.Event()
        self.detect_worker = None
        self.is_detecting = False
        self.is_batch_detection = False
        self._all_model_paths: list[Path] = []
        self._model_display_paths: dict[str, Path] = {}
        self.source_items: list[Path] = []
        self.source_index = -1
        self.result_by_source: dict[str, dict] = {}
        self.user_selected_result = False
        self.result_nav_buttons: list[QPushButton] = []
        self.log_queue: Queue | None = None
        self.stop_requested = False
        self._yaml_restore_path: Path | None = None
        self._yaml_restore_text: str | None = None
        self._yaml_restore_pending = False
        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(150)
        self.poll_timer.timeout.connect(self.poll_validation_queue)
        layout = self.page_layout()
        split = QHBoxLayout()
        layout.addLayout(split, 1)

        # Left column
        left_shell = Card()
        left_column = left_shell.layout
        validation = app.settings["validation"]

        model_title = QLabel("模型配置")
        model_title.setObjectName("sectionTitle")
        left_column.addWidget(model_title)
        model_box, self.model_combo = self.stacked_combo_field(
            "选择模型",
            "",
            [],
            browse=lambda combo: self._choose_pt_for_combo(combo),
            placeholder="选择或输入模型路径",
        )
        self.model_combo.setMinimumWidth(140)
        left_column.addWidget(model_box)

        conf_row = QHBoxLayout()
        self.conf_box, self.conf_edit = self.field(
            "置信度",
            str(validation["confidence"]),
            placeholder="例如 0.25",
        )
        self.iou_box, self.iou_edit = self.field(
            "IoU",
            str(validation["iou"]),
            placeholder="例如 0.45",
        )
        self.imgsz_box, self.imgsz_combo = self.combo_field(
            "图片尺寸",
            str(validation.get("imgsz", 640)),
            ["640", "960", "1280"],
            editable=True,
            placeholder="例如 640",
        )
        self.imgsz_combo.setMinimumContentsLength(5)
        conf_row.addWidget(self.conf_box)
        conf_row.addWidget(self.iou_box)
        conf_row.addWidget(self.imgsz_box)
        left_column.addLayout(conf_row)

        # Source config
        self.mode_box, self.mode_combo = self.combo_field(
            "检测模式",
            validation.get("source_mode", "图片/视频文件夹"),
            ["图片/视频文件夹", "图片/视频", "摄像头", "数据集验证"],
        )
        left_column.addWidget(self.mode_box)
        initial_source_text = validation["source_path"] or validation.get(
            "source_scope", "全部图片"
        )
        self.source_box, self.source_combo = self.stacked_combo_field(
            "输入源",
            initial_source_text,
            SOURCE_SCOPE_OPTIONS,
            browse=lambda combo: self.choose_detection_source(combo),
            placeholder="选择输入源或自定义图片文件夹",
        )
        left_column.addWidget(self.source_box)
        self.data_box, self.data_edit = self.path_field(
            "数据集 YAML",
            validation.get("data", ""),
            self.choose_dataset_yaml,
            "选择 data.yaml",
        )
        left_column.addWidget(self.data_box)
        self.source_scope_box, self.source_scope_combo = self.combo_field(
            "选择验证源",
            validation.get("source_scope", "全部图片"),
            SOURCE_SCOPE_OPTIONS,
        )
        left_column.addWidget(self.source_scope_box)
        self.camera_box, self.camera_combo = self.combo_field(
            "摄像头",
            str(validation["camera_index"]),
            ["0", "1", "2", "3"],
        )
        left_column.addWidget(self.camera_box)
        self.save_box, self.save_edit = self.path_field(
            "输出文件夹",
            validation["save_dir"],
            self.choose_output_dir,
            "选择结果输出目录",
        )
        left_column.addWidget(self.save_box)

        controls = QHBoxLayout()
        self.start_det_btn = QPushButton("批量检测")
        self.start_det_btn.clicked.connect(self.start_detection)
        self.stop_det_btn = QPushButton("停止")
        self.stop_det_btn.setObjectName("softButton")
        self.stop_det_btn.setEnabled(False)
        self.stop_det_btn.clicked.connect(self.stop_detection)
        controls.addWidget(self.start_det_btn)
        controls.addWidget(self.stop_det_btn)
        left_column.addLayout(controls)
        self.open_val_save_btn = QPushButton("打开保存目录")
        self.open_val_save_btn.setObjectName("softButton")
        self.open_val_save_btn.clicked.connect(self.open_detection_save_dir)
        self.open_val_save_btn.setVisible(False)
        left_column.addWidget(self.open_val_save_btn)
        self.detect_log = QTextEdit()
        self.prepare_readonly_text(self.detect_log)
        self.detect_log.setMinimumHeight(180)
        left_column.addWidget(self.detect_log)
        left_column.addStretch(1)
        split.addWidget(left_shell)

        # Right column
        right = QVBoxLayout()
        self.toolbar_widget = QWidget()
        toolbar = QHBoxLayout(self.toolbar_widget)
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.addWidget(QLabel("批量检测结果"))
        for text, slot in [
            ("上一张", self.prev_result),
            ("下一张", self.next_result),
            ("第一张", self.first_result),
            ("最后一张", self.last_result),
            ("列表", self.show_result_list),
            ("打开保存文件夹", self.open_detection_save_dir),
        ]:
            button = QPushButton(text)
            button.setObjectName("softButton")
            button.clicked.connect(slot)
            toolbar.addWidget(button)
            if text != "打开保存文件夹":
                self.result_nav_buttons.append(button)
        self.counter = QLabel("0/0")
        toolbar.addWidget(self.counter)
        toolbar.addStretch(1)
        right.addWidget(self.toolbar_widget)
        self.views_widget = QWidget()
        views = QHBoxLayout(self.views_widget)
        views.setContentsMargins(0, 0, 0, 0)
        source_panel = Card("源")
        self.source_view = ImageView("源图")
        source_panel.layout.addWidget(self.source_view, 1)
        result_panel = Card("检测结果")
        self.result_view = ImageView("检测结果图")
        result_panel.layout.addWidget(self.result_view, 1)
        views.addWidget(source_panel)
        views.addWidget(result_panel)
        right.addWidget(self.views_widget, 2)
        self.table_panel = Card("检测结果详情表")
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["类别", "置信度", "坐标(x,y)", "尺寸(w×h)", "角度"]
        )
        self.table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table_panel.layout.addWidget(self.table)
        right.addWidget(self.table_panel, 1)
        self.val_log_panel = Card("验证日志")
        self.val_log = QTextEdit()
        self.prepare_readonly_text(self.val_log)
        self.val_log_panel.layout.addWidget(self.val_log, 1)
        self.val_log.setMinimumHeight(220)
        right.addWidget(self.val_log_panel, 1)
        right_widget = QWidget()
        right_widget.setLayout(right)
        split.addWidget(right_widget)
        split.setStretch(0, 1)
        split.setStretch(1, 3)

        self.mode_combo.currentTextChanged.connect(self.update_source_mode)
        self.update_source_mode(self.mode_combo.currentText())
        self.update_detection_button_text()

    def update_source_mode(self, value):
        camera = value == "摄像头"
        single_file_mode = value == "图片/视频"
        dataset_source_mode = value == "图片/视频文件夹"
        val_mode = self.is_val_mode(value)
        self.source_box.setVisible(single_file_mode or dataset_source_mode)
        self.data_box.setVisible(val_mode)
        self.source_scope_box.setVisible(val_mode)
        self.camera_box.setVisible(camera)
        self.save_box.setVisible(True)
        self.open_val_save_btn.setVisible(val_mode)
        self.set_result_navigation_enabled((not camera) and (not val_mode))
        self.detect_log.setVisible(not val_mode)
        self.toolbar_widget.setVisible(not val_mode)
        self.views_widget.setVisible(not val_mode)
        self.table_panel.setVisible(not val_mode)
        self.val_log_panel.setVisible(val_mode)
        if camera:
            self.counter.setText("实时预览")
        elif val_mode:
            self.counter.setText("验证模式")
        elif not self.detect_results:
            self.counter.setText("0/0")
        if dataset_source_mode:
            self._configure_source_combo(
                SOURCE_SCOPE_OPTIONS,
                self.app.settings.get("validation", {}).get("source_path")
                or self.app.settings.get("validation", {}).get("source_scope", "全部图片"),
                "可选：选择自定义图片文件夹；也可直接选择固定来源",
            )
        elif single_file_mode:
            self._configure_source_combo(
                [],
                self.app.settings.get("validation", {}).get("source_path", ""),
                "选择图片或视频",
            )
        self.update_detection_button_text()
        self.refresh_source_items()

    def is_val_mode(self, value: str | None = None) -> bool:
        return str(value or self.mode_combo.currentText()).strip() == "数据集验证"

    def _configure_source_combo(
        self, values: list[str], current_text: str, placeholder: str
    ) -> None:
        self.source_combo.blockSignals(True)
        self.source_combo.clear()
        self.source_combo.addItems(values)
        self.source_combo.setCurrentText(str(current_text or ""))
        line_edit = self.source_combo.lineEdit()
        if line_edit is not None:
            line_edit.setPlaceholderText(placeholder)
        self.source_combo.blockSignals(False)

    def set_result_navigation_enabled(self, enabled: bool):
        for button in self.result_nav_buttons:
            button.setEnabled(enabled)

    def update_detection_button_text(self):
        mode = self.mode_combo.currentText()
        if self.is_val_mode(mode):
            self.start_det_btn.setText("开始验证")
            self.stop_det_btn.setText("停止")
            return
        self.start_det_btn.setText("开始检测" if mode == "图片/视频" else "批量检测")
        self.stop_det_btn.setText("停止")

    def choose_detection_source(self, combo: QComboBox):
        current_text = combo.currentText().strip()
        current = (
            self.resolve_combo_path_text(current_text)
            if current_text and current_text not in SOURCE_SCOPE_OPTIONS
            else str(self.project_root())
        )
        if self.mode_combo.currentText() == "图片/视频":
            path, _ = QFileDialog.getOpenFileName(
                self,
                "选择图片或视频",
                current,
                "图片/视频 (*.jpg *.jpeg *.png *.bmp *.mp4 *.avi *.mov *.mkv);;所有文件 (*)",
            )
            if path:
                combo.setCurrentText(self.display_path(path))
                self.refresh_source_items()
            return
        path = QFileDialog.getExistingDirectory(self, "选择图片文件夹", current)
        if path:
            combo.setCurrentText(self.display_path(path))
            self.refresh_source_items()

    def choose_dataset_yaml(self, edit: QLineEdit):
        current = self.resolve_path_text(edit) if edit.text() else str(self.project_root())
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择数据集 YAML",
            current,
            "YAML 文件 (*.yaml *.yml);;所有文件 (*)",
        )
        if path:
            edit.setText(self.display_path(path))

    def choose_output_dir(self, edit: QLineEdit):
        self.choose_dir(edit)

    def refresh_source_items(self):
        if self.mode_combo.currentText() == "摄像头" or self.is_val_mode():
            self.source_items = []
            self.source_index = -1
            return
        source_path = self._folder_source_path_for_selection()
        if self.mode_combo.currentText() == "图片/视频":
            source_path = self.resolve_combo_path_text(self.source_combo.currentText())
        self.source_items = collect_prediction_sources(
            self.mode_combo.currentText(),
            source_path,
        )
        if not self.source_items:
            self.source_index = -1
            return
        if self.source_index < 0 or self.source_index >= len(self.source_items):
            self.source_index = 0

    def _dataset_split_dir(self, split: str) -> Path:
        dataset_dir = Path(self.app.settings["paths"]["dataset_dir"])
        return (dataset_dir / split / "images").resolve()

    def _scope_target_path(self, scope: str) -> Path:
        scope = str(scope or "全部图片").strip()
        if scope == "全部图片":
            return Path(self.app.settings["paths"]["images_dir"]).resolve()
        if scope == "训练图片":
            return self._dataset_split_dir("train")
        if scope == "验证图片":
            return self._dataset_split_dir("val")
        if scope == "测试图片":
            return self._dataset_split_dir("test")
        return Path(self.app.settings["paths"]["images_dir"]).resolve()

    def _folder_source_path_for_selection(self) -> str:
        text = self.source_combo.currentText().strip()
        if text in SOURCE_SCOPE_OPTIONS:
            return str(self._scope_target_path(text))
        return self.resolve_combo_path_text(text)

    def on_show(self):
        self.refresh_model_choices(self.app.settings["validation"].get("model_path", ""))
        self._connect_validation_persistence()

    def refresh_model_choices(self, preferred_model: str | None = None):
        current_text = preferred_model
        if current_text is None:
            current_text = self.model_combo.currentText()
        project_root = self.project_root()
        result_dir = Path(self.app.settings["paths"]["result_dir"])
        show_last = self.app.settings.get("features", {}).get(
            "show_last_training_models", False
        )
        current_path = None
        mapped_current = self._model_display_paths.get(str(current_text or "").strip())
        if mapped_current is not None:
            current_path = mapped_current
        elif current_text:
            current_path = Path(current_text)
            if not current_path.is_absolute():
                current_path = Path(self.resolve_combo_path_text(str(current_text)))
        self._all_model_paths = []
        self._model_display_paths = {}
        seen: set[str] = set()
        for path in _find_models_full_paths(
            result_dir, show_last_training_models=show_last
        ):
            resolved_path = path.resolve()
            resolved = str(resolved_path)
            if resolved in seen:
                continue
            self._all_model_paths.append(resolved_path)
            display_name = _simplified_model_path(str(resolved_path), project_root)
            self._model_display_paths[display_name] = resolved_path
            seen.add(resolved)
        display_names = list(self._model_display_paths.keys())
        selected_display = str(current_text or "").strip()
        if current_path:
            for display_name, resolved_path in self._model_display_paths.items():
                if resolved_path == current_path:
                    selected_display = display_name
                    break
            else:
                if (
                    not show_last
                    and current_path.name.lower() == "last.pt"
                    and current_path.parent.name.lower() == "weights"
                ):
                    best_path = current_path.with_name("best.pt")
                    best_display = _simplified_model_path(str(best_path), project_root)
                    if best_display in self._model_display_paths:
                        selected_display = best_display
                elif current_path.exists():
                    selected_display = _simplified_model_path(str(current_path), project_root)
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        self.model_combo.addItems(display_names)
        self.model_combo.setCurrentText(selected_display)
        self.model_combo.blockSignals(False)

    def _connect_validation_persistence(self):
        if getattr(self, "_persistence_connected", False):
            return
        self._persistence_connected = True
        self.model_combo.currentTextChanged.connect(self._persist_validation_model)
        self.mode_combo.currentTextChanged.connect(
            lambda value: self._persist_validation_value("source_mode", value)
        )
        self.source_combo.currentTextChanged.connect(
            lambda _text: self._handle_source_input_changed()
        )
        self.data_edit.textChanged.connect(
            lambda _text: self._handle_data_path_changed()
        )
        self.source_scope_combo.currentTextChanged.connect(
            lambda value: self._handle_source_scope_changed(value)
        )
        self.save_edit.textChanged.connect(
            lambda _text: self._persist_validation_value(
                "save_dir", self.resolve_path_text(self.save_edit)
            )
        )
        self.camera_combo.currentTextChanged.connect(
            lambda value: self._persist_validation_value("camera_index", int(value))
        )
        self.conf_edit.textChanged.connect(
            lambda text: self._persist_validation_numeric("confidence", text)
        )
        self.iou_edit.textChanged.connect(
            lambda text: self._persist_validation_numeric("iou", text)
        )
        self.imgsz_combo.currentTextChanged.connect(
            lambda text: self._persist_validation_integer("imgsz", text)
        )

    def _persist_validation_model(self, _text: str):
        self.app.settings.setdefault("validation", {})["model_path"] = (
            self._get_model_path()
        )
        self.save_settings()

    def _persist_validation_value(self, key: str, value):
        self.app.settings.setdefault("validation", {})[key] = value
        self.save_settings()

    def _handle_source_input_changed(self):
        text = self.source_combo.currentText().strip()
        if self.mode_combo.currentText() == "图片/视频文件夹":
            if text in SOURCE_SCOPE_OPTIONS:
                self._persist_validation_value("source_scope", text)
                self._persist_validation_value("source_path", "")
            else:
                self._persist_validation_value(
                    "source_path", self.resolve_combo_path_text(text)
                )
        else:
            self._persist_validation_value("source_path", self.resolve_combo_path_text(text))
        self.refresh_source_items()

    def _handle_data_path_changed(self):
        self._persist_validation_value("data", self.resolve_path_text(self.data_edit))
        self.refresh_source_items()

    def _handle_source_scope_changed(self, value: str):
        self._persist_validation_value("source_scope", value)
        self.refresh_source_items()

    def _persist_validation_numeric(self, key: str, text: str):
        try:
            value = float(text)
        except ValueError:
            value = text
        self._persist_validation_value(key, value)

    def _persist_validation_integer(self, key: str, text: str):
        try:
            value = int(text)
        except ValueError:
            value = text
        self._persist_validation_value(key, value)

    def _get_model_path(self) -> str:
        """Resolve the selected model combo to an absolute path."""
        text = self.model_combo.currentText()
        mapped = self._model_display_paths.get(text)
        if mapped is not None:
            return str(mapped)
        # Try to find it in our known paths
        for p in self._all_model_paths:
            if (
                _simplified_model_path(str(p), self.project_root()) == text
                or self.display_path(p) == text
                or str(p) == text
            ):
                return str(p)
        # Maybe it's already a full path
        if Path(text).exists():
            return text
        resolved = self.resolve_combo_path_text(text)
        return resolved if resolved else text

    def resolve_combo_path_text(self, text: str) -> str:
        return _resolve_project_path(text, self.project_root())

    def config(self):
        return {
            "model_path": self._get_model_path(),
            "source_mode": self.mode_combo.currentText(),
            "source_path": self._folder_source_path_for_selection()
            if self.mode_combo.currentText() == "图片/视频文件夹"
            else self.resolve_combo_path_text(self.source_combo.currentText()),
            "data": self.resolve_path_text(self.data_edit),
            "source_scope": self.source_scope_combo.currentText(),
            "camera_index": int(self.camera_combo.currentText()),
            "confidence": float(self.conf_edit.text()),
            "iou": float(self.iou_edit.text()),
            "imgsz": int(self.imgsz_combo.currentText()),
            "save_dir": self.resolve_path_text(self.save_edit),
        }

    def single_file_config(self, path: Path) -> dict:
        config = self.config()
        config["source_mode"] = "图片/视频"
        config["source_path"] = str(path)
        return config

    def _dataset_yaml_root(self, payload: dict, data_path: Path) -> Path:
        root_value = payload.get("path")
        if not root_value:
            return data_path.parent.resolve()
        root = Path(str(root_value))
        if root.is_absolute():
            return root.resolve()
        return (data_path.parent / root).resolve()

    def _val_override_value_for_scope(self, data_path: Path, scope: str) -> str:
        target = self._scope_target_path(scope)
        payload = yaml.safe_load(data_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return str(target)
        dataset_root = self._dataset_yaml_root(payload, data_path)
        if scope == "全部图片":
            images_dir = Path(self.app.settings["paths"]["images_dir"]).resolve()
            if target == images_dir:
                return "images"
        try:
            relative = os.path.relpath(str(target), str(dataset_root))
            return str(Path(relative))
        except ValueError:
            return str(target)

    def _prepare_temporary_validation_yaml(self, data_path: Path, scope: str) -> None:
        original_text = data_path.read_text(encoding="utf-8")
        payload = yaml.safe_load(original_text)
        if not isinstance(payload, dict):
            return
        payload["val"] = self._val_override_value_for_scope(data_path, scope)
        patched_text = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
        if patched_text == original_text:
            return
        data_path.write_text(patched_text, encoding="utf-8")
        self._yaml_restore_path = data_path
        self._yaml_restore_text = original_text
        self._yaml_restore_pending = True

    def _restore_temporary_validation_yaml_if_needed(self) -> None:
        if not self._yaml_restore_pending or self._yaml_restore_path is None:
            return
        if self._yaml_restore_text is not None:
            self._yaml_restore_path.write_text(
                self._yaml_restore_text, encoding="utf-8"
            )
        self._yaml_restore_pending = False
        self._yaml_restore_path = None
        self._yaml_restore_text = None

    def clear_active_log(self):
        self.detect_log.clear()
        self.val_log.clear()

    def append_active_log(self, text: str):
        if self.is_val_mode():
            self.val_log.append(text)
            return
        self.detect_log.append(text)

    # Task 9: Only allow one detection at a time
    def start_detection(self):
        if self.is_detecting:
            return
        if self.is_val_mode():
            self.start_dataset_validation()
            return
        self.refresh_source_items()
        if self.mode_combo.currentText() == "图片/视频":
            if not self.source_items:
                QMessageBox.information(
                    self,
                    "输入源为空",
                    "请先选择有效的输入源，或确认 data.yaml 中所选来源下存在图片/视频。",
                )
                return
            self.source_index = max(
                0, min(self.source_index, len(self.source_items) - 1)
            )
            self.start_current_source_detection()
            return
        self.is_detecting = True
        self.start_det_btn.setEnabled(False)
        self.stop_det_btn.setEnabled(True)
        self.detect_log.clear()
        self.detect_stop.clear()
        self.detect_results.clear()
        self.result_by_source.clear()
        self.user_selected_result = False
        self.is_batch_detection = not _is_live_source_mode(
            self.mode_combo.currentText()
        )
        self.detect_index = -1
        self.clear_active_log()
        self.counter.setText(
            "实时预览"
            if _is_live_source_mode(self.mode_combo.currentText())
            else "0/0"
        )
        self.table.setRowCount(0)
        self.app.status.setText("检测中")
        self.detect_worker = DetectionWorker(self.config(), self.detect_stop)
        self.detect_worker.result_payload.connect(self.handle_result)
        self.detect_worker.finished_with_results.connect(self.apply_detect_done)
        self.detect_worker.failed.connect(self.apply_detect_error)
        self.detect_worker.start()

    def start_dataset_validation(self):
        config = self.config()
        if not config["model_path"]:
            QMessageBox.information(self, "模型为空", "请选择一个用于验证的模型。")
            return
        if not config["data"] or not Path(config["data"]).exists():
            QMessageBox.information(self, "数据集 YAML 为空", "请选择有效的 data.yaml。")
            return
        self._prepare_temporary_validation_yaml(
            Path(config["data"]), config["source_scope"]
        )
        self.is_detecting = True
        self.is_batch_detection = False
        self.stop_requested = False
        self.start_det_btn.setEnabled(False)
        self.stop_det_btn.setEnabled(True)
        self.clear_active_log()
        command = build_val_command(config)
        self.append_active_log(" ".join(command))
        self.log_queue = Queue()
        self.app.validation_handle = spawn_logged_process(
            command, str(ROOT), self.log_queue
        )
        self.poll_timer.start()
        self.table.setRowCount(0)
        self.counter.setText("验证中")
        self.app.status.setText("验证中")

    def start_current_source_detection(self):
        if not self.source_items:
            return
        self.source_index = max(
            0, min(self.source_index, len(self.source_items) - 1)
        )
        self.start_single_detection(self.source_items[self.source_index])

    def start_single_detection(self, path: Path):
        if self.is_detecting:
            return
        self.refresh_source_items()
        source_key = str(Path(path).resolve())
        cached = self.result_by_source.get(source_key)
        if cached:
            self.detect_index = (
                self.detect_results.index(cached)
                if cached in self.detect_results
                else self.detect_index
            )
            self.show_detection_payload(cached)
            return
        self.is_detecting = True
        self.is_batch_detection = False
        self.start_det_btn.setEnabled(False)
        self.stop_det_btn.setEnabled(True)
        self.detect_stop.clear()
        self.app.status.setText("检测中")
        self.detect_worker = DetectionWorker(
            self.single_file_config(path), self.detect_stop
        )
        self.detect_worker.result_payload.connect(self.handle_result)
        self.detect_worker.finished_with_results.connect(self.apply_detect_done)
        self.detect_worker.failed.connect(self.apply_detect_error)
        self.detect_worker.start()

    def apply_detect_done(self, results):
        self.append_active_log("检测任务结束。")
        self.app.status.setText("检测结束")
        self.detect_worker = None
        self.is_detecting = False
        self.start_det_btn.setEnabled(True)
        self.stop_det_btn.setEnabled(False)

    def apply_detect_error(self, message):
        self.append_active_log(message)
        self.app.status.setText("检测异常")
        self.detect_worker = None
        self.is_detecting = False
        self.start_det_btn.setEnabled(True)
        self.stop_det_btn.setEnabled(False)

    def stop_detection(self):
        if not self.is_detecting:
            return
        if self.is_val_mode():
            self.stop_requested = True
            self.stop_det_btn.setEnabled(False)
            self.app.status.setText("停止验证中")
            stop_process(getattr(self.app, "validation_handle", None))
            self.append_active_log("已请求停止验证。")
            return
        self.detect_stop.set()
        self.stop_det_btn.setEnabled(False)
        self.append_active_log("已请求停止检测。")
        self.app.status.setText("停止检测中")

    def poll_validation_queue(self):
        if self.log_queue is None:
            self._recover_validation_state_if_process_exited()
            return
        while not self.log_queue.empty():
            event, payload = self.log_queue.get()
            if event == "log":
                if self.stop_requested:
                    continue
                self.append_active_log(payload)
            elif event == "exit":
                self._finish_dataset_validation(payload)
                return
        self._recover_validation_state_if_process_exited()

    def _recover_validation_state_if_process_exited(self):
        handle = getattr(self.app, "validation_handle", None)
        if not self.is_detecting or handle is None or not self.is_val_mode():
            return
        exit_code = handle.process.poll()
        if exit_code is None:
            return
        self._finish_dataset_validation(exit_code)

    def _finish_dataset_validation(self, exit_code: int):
        self._restore_temporary_validation_yaml_if_needed()
        if self.stop_requested:
            self.append_active_log("验证已停止。")
            self.app.status.setText("验证已停止")
        else:
            self.append_active_log(f"验证进程结束，退出码：{exit_code}")
            self.app.status.setText("验证结束" if exit_code == 0 else "验证异常结束")
        self.poll_timer.stop()
        self.is_detecting = False
        self.stop_requested = False
        self.start_det_btn.setEnabled(True)
        self.stop_det_btn.setEnabled(False)
        self.log_queue = None
        self.app.validation_handle = None
        self.counter.setText("验证模式")

    def handle_result(self, payload):
        if _is_live_source_mode(self.mode_combo.currentText()):
            self.detect_index = 0
            self.show_detection_payload(payload)
            return
        if not _should_store_detection_history(self.mode_combo.currentText()):
            self.show_detection_payload(payload)
            return
        self.detect_results.append(payload)
        source_path = payload.get("source_path")
        if source_path:
            self.result_by_source[str(Path(source_path).resolve())] = payload
        # Task 14: For batch, always show the first image
        if len(self.detect_results) == 1 or (
            not self.is_batch_detection and not self.user_selected_result
        ):
            self.detect_index = len(self.detect_results) - 1
            self.show_detection_payload(payload)
        else:
            # Just update counter and log, don't switch view
            self.counter.setText(
                _detection_counter_text(
                    self.mode_combo.currentText(),
                    self.detect_index,
                    len(self.detect_results),
                )
            )
            self.append_active_log(_build_detection_log_message(payload))

    def show_detection_payload(self, payload):
        self.source_view.set_pil_image(payload["source_image"])
        self.result_view.set_pil_image(payload["result_image"])
        self.table.setRowCount(len(payload["items"]))
        for row, item in enumerate(payload["items"]):
            values = [
                item.label,
                f"{item.confidence:.3f}",
                f"({item.center_x:.1f}, {item.center_y:.1f})",
                f"{item.width:.1f}×{item.height:.1f}",
                f"{item.angle:.1f}",
            ]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))
        self.counter.setText(
            _detection_counter_text(
                self.mode_combo.currentText(),
                self.detect_index,
                len(self.detect_results),
            )
        )
        self.append_active_log(_build_detection_log_message(payload))

    def first_result(self):
        if not self.detect_results:
            return
        self.user_selected_result = True
        self.detect_index = 0
        self.show_detection_payload(self.detect_results[0])

    def last_result(self):
        if not self.detect_results:
            return
        self.user_selected_result = True
        self.detect_index = len(self.detect_results) - 1
        self.show_detection_payload(self.detect_results[-1])

    def prev_result(self):
        if not self.detect_results:
            return
        self.user_selected_result = True
        self.detect_index = (self.detect_index - 1) % len(self.detect_results)
        self.show_detection_payload(self.detect_results[self.detect_index])

    def next_result(self):
        if not self.detect_results:
            return
        self.user_selected_result = True
        self.detect_index = (self.detect_index + 1) % len(self.detect_results)
        self.show_detection_payload(self.detect_results[self.detect_index])

    def show_source_index(self, index: int):
        self.refresh_source_items()
        if not self.source_items:
            return
        self.source_index = index % len(self.source_items)

    def show_cached_source_result(self, path: Path) -> bool:
        cached = self.result_by_source.get(str(Path(path).resolve()))
        if not cached:
            return False
        self.user_selected_result = True
        self.detect_index = self.detect_results.index(cached)
        self.show_detection_payload(cached)
        return True

    def show_result_list(self):
        self.refresh_source_items()
        if not self.source_items:
            QMessageBox.information(
                self, "输入源列表", "当前输入源没有可选择的图片或视频。"
            )
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("输入源列表")
        dialog.resize(320, 520)
        dialog.setMinimumSize(200, 200)
        layout = QVBoxLayout(dialog)
        listing = QListWidget()
        layout.addWidget(listing, 1)
        search = QLineEdit()
        search.setPlaceholderText("搜索文件名")
        layout.addWidget(search)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        layout.addWidget(buttons)
        visible_paths: list[Path] = []

        def filter_items(text: str = ""):
            nonlocal visible_paths
            needle = text.strip().lower()
            visible_paths = [
                path
                for path in self.source_items
                if not needle or needle in path.name.lower()
            ]
            listing.clear()
            for path in visible_paths:
                listing.addItem(path.name)
            if visible_paths:
                current_path = (
                    self.source_items[self.source_index]
                    if 0 <= self.source_index < len(self.source_items)
                    else visible_paths[0]
                )
                current_row = (
                    visible_paths.index(current_path)
                    if current_path in visible_paths
                    else 0
                )
                listing.setCurrentRow(current_row)

        def jump_to_current():
            row = listing.currentRow()
            if 0 <= row < len(visible_paths):
                path = visible_paths[row]
                self.source_index = self.source_items.index(path)
                self.show_cached_source_result(path)
            dialog.accept()

        filter_items()
        search.textChanged.connect(filter_items)
        listing.itemDoubleClicked.connect(lambda _item: jump_to_current())
        buttons.accepted.connect(jump_to_current)
        buttons.rejected.connect(dialog.reject)
        dialog.exec()

    def open_detection_save_dir(self):
        save_dir = Path(self.resolve_path_text(self.save_edit))
        save_dir.mkdir(parents=True, exist_ok=True)
        os.startfile(save_dir)

# ===================================================================
#  Task 13: Settings page - system info style + auto-refresh
#  Task 10: Custom command toggle
# ===================================================================
