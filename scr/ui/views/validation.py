from __future__ import annotations

import os
import threading
from pathlib import Path

from scr.services.detection_service import collect_prediction_sources
from scr.ui.helpers import _build_detection_log_message, _detection_counter_text, _find_models_full_paths, _is_live_source_mode, _should_store_detection_history, _simplified_model_path, _resolve_project_path
from scr.ui.page_base import BasePage, Card, ImageView
from scr.ui.qt import Qt, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget
from scr.ui.workers import DetectionWorker

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
        layout = self.page_layout()
        split = QHBoxLayout()
        layout.addLayout(split, 1)

        # Left column
        left_shell = Card()
        left_column = left_shell.layout
        validation = app.settings["validation"]

        # Model config - Task 14: dropdown for models
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
            "图片/视频文件夹",
            ["图片/视频文件夹", "图片/视频", "摄像头"],
        )
        left_column.addWidget(self.mode_box)
        self.source_box, self.source_edit = self.path_field(
            "输入源",
            validation["source_path"],
            self.choose_detection_source,
            "选择图片、视频或文件夹",
        )
        left_column.addWidget(self.source_box)
        self.camera_box, self.camera_combo = self.combo_field(
            "摄像头",
            str(validation["camera_index"]),
            ["0", "1", "2", "3"],
        )
        left_column.addWidget(self.camera_box)

        controls = QHBoxLayout()
        self.start_det_btn = QPushButton("批量检测")
        self.start_det_btn.clicked.connect(self.start_detection)
        pause = QPushButton("暂停")
        pause.setObjectName("softButton")
        controls.addWidget(self.start_det_btn)
        controls.addWidget(pause)
        left_column.addLayout(controls)

        log_title = QLabel("检测日志")
        log_title.setObjectName("sectionTitle")
        left_column.addWidget(log_title)
        self.detect_log = QTextEdit()
        self.prepare_readonly_text(self.detect_log)
        left_column.addWidget(self.detect_log, 1)
        split.addWidget(left_shell)

        # Right column
        right = QVBoxLayout()
        toolbar = QHBoxLayout()
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
        right.addLayout(toolbar)
        views = QHBoxLayout()
        source_panel = Card("源")
        self.source_view = ImageView("源图")
        source_panel.layout.addWidget(self.source_view, 1)
        result_panel = Card("检测结果")
        self.result_view = ImageView("检测结果图")
        result_panel.layout.addWidget(self.result_view, 1)
        views.addWidget(source_panel)
        views.addWidget(result_panel)
        right.addLayout(views, 2)
        table_panel = Card("检测结果详情表")
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
        table_panel.layout.addWidget(self.table)
        right.addWidget(table_panel, 1)
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
        self.source_box.setVisible(not camera)
        self.camera_box.setVisible(camera)
        self.set_result_navigation_enabled(not camera)
        if camera:
            self.counter.setText("实时预览")
        elif not self.detect_results:
            self.counter.setText("0/0")
        self.update_detection_button_text()
        self.refresh_source_items()

    def set_result_navigation_enabled(self, enabled: bool):
        for button in self.result_nav_buttons:
            button.setEnabled(enabled)

    def update_detection_button_text(self):
        self.start_det_btn.setText(
            "开始检测"
            if self.mode_combo.currentText() == "图片/视频"
            else "批量检测"
        )

    def choose_detection_source(self, edit: QLineEdit):
        current = (
            self.resolve_path_text(edit)
            if edit.text()
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
                edit.setText(self.display_path(path))
                self.refresh_source_items()
            return
        self.choose_dir(edit)
        self.refresh_source_items()

    def refresh_source_items(self):
        if self.mode_combo.currentText() == "摄像头":
            self.source_items = []
            self.source_index = -1
            return
        self.source_items = collect_prediction_sources(
            self.mode_combo.currentText(), self.resolve_path_text(self.source_edit)
        )
        if not self.source_items:
            self.source_index = -1
            return
        if self.source_index < 0 or self.source_index >= len(self.source_items):
            self.source_index = 0

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
        self.source_edit.textChanged.connect(
            lambda _text: self._persist_validation_value(
                "source_path", self.resolve_path_text(self.source_edit)
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
            "source_path": self.resolve_path_text(self.source_edit),
            "camera_index": int(self.camera_combo.currentText()),
            "confidence": float(self.conf_edit.text()),
            "iou": float(self.iou_edit.text()),
            "imgsz": int(self.imgsz_combo.currentText()),
            "save_dir": self.app.settings["validation"]["save_dir"],
        }

    def single_file_config(self, path: Path) -> dict:
        config = self.config()
        config["source_mode"] = "图片/视频"
        config["source_path"] = str(path)
        return config

    # Task 9: Only allow one detection at a time
    def start_detection(self):
        if self.is_detecting:
            return
        self.refresh_source_items()
        if self.mode_combo.currentText() == "图片/视频":
            if not self.source_items:
                QMessageBox.information(
                    self, "输入源为空", "请选择一张图片或一段视频。"
                )
                return
            self.source_index = max(
                0, min(self.source_index, len(self.source_items) - 1)
            )
            self.start_current_source_detection()
            return
        self.is_detecting = True
        self.start_det_btn.setEnabled(False)
        self.detect_log.clear()
        self.detect_stop.clear()
        self.detect_results.clear()
        self.result_by_source.clear()
        self.user_selected_result = False
        self.is_batch_detection = not _is_live_source_mode(
            self.mode_combo.currentText()
        )
        self.detect_index = -1
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
        self.detect_log.append("检测任务结束。")
        self.app.status.setText("检测结束")
        self.detect_worker = None
        self.is_detecting = False
        self.start_det_btn.setEnabled(True)

    def apply_detect_error(self, message):
        self.detect_log.append(message)
        self.app.status.setText("检测异常")
        self.detect_worker = None
        self.is_detecting = False
        self.start_det_btn.setEnabled(True)

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
            self.detect_log.append(_build_detection_log_message(payload))

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
        self.detect_log.append(_build_detection_log_message(payload))

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
        save_dir = Path(self.app.settings["validation"]["save_dir"])
        save_dir.mkdir(parents=True, exist_ok=True)
        os.startfile(save_dir)

# ===================================================================
#  Task 13: Settings page - system info style + auto-refresh
#  Task 10: Custom command toggle
# ===================================================================
