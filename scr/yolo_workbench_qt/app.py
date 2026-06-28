from __future__ import annotations

import json
import os
import sys
import threading
import traceback
from pathlib import Path
from queue import Queue

from PIL import Image

from scr.yolo_workbench.services.annotation_service import load_yolo_annotations, render_annotation_preview
from scr.yolo_workbench.services.conversion_service import ConversionConfig, preview_conversion, run_conversion
from scr.yolo_workbench.services.detection_service import run_prediction, scan_candidate_models
from scr.yolo_workbench.services.environment_service import detect_modules, pixi_available, system_status, torch_cuda_summary
from scr.yolo_workbench.services.rename_service import execute_rename, preview_rename
from scr.yolo_workbench.services.resize_service import ResizeConfig, preview_resize, run_resize
from scr.yolo_workbench.services.runtime_service import spawn_logged_process, stop_process
from scr.yolo_workbench.services.settings_service import ROOT, SettingsService
from scr.yolo_workbench.services.training_service import build_train_command, infer_task_mode_from_model


def run_app() -> None:
    try:
        from PySide6.QtCore import Qt, QThread, QTimer, Signal
        from PySide6.QtGui import QFont, QImage, QPixmap
        from PySide6.QtWidgets import (
            QApplication,
            QCheckBox,
            QComboBox,
            QFileDialog,
            QFrame,
            QGridLayout,
            QHBoxLayout,
            QHeaderView,
            QLabel,
            QLineEdit,
            QMainWindow,
            QMessageBox,
            QPushButton,
            QProgressBar,
            QScrollArea,
            QSizePolicy,
            QStackedWidget,
            QTableWidget,
            QTableWidgetItem,
            QTabWidget,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )
    except ModuleNotFoundError as exc:
        raise SystemExit(f"缺少 Qt 依赖：{exc.name}。请先执行 pixi install 后运行 pixi run app。") from exc

    IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp"}

    def pil_to_pixmap(image: Image.Image) -> QPixmap:
        rgba = image.convert("RGBA")
        data = rgba.tobytes("raw", "RGBA")
        qimage = QImage(data, rgba.width, rgba.height, rgba.width * 4, QImage.Format.Format_RGBA8888)
        return QPixmap.fromImage(qimage.copy())

    class Worker(QThread):
        finished_with_payload = Signal(str, object)

        def __init__(self, kind: str, fn):
            super().__init__()
            self.kind = kind
            self.fn = fn

        def run(self):
            try:
                payload = self.fn()
            except Exception:
                payload = {"error": traceback.format_exc()}
            self.finished_with_payload.emit(self.kind, payload)

    class DetectionWorker(QThread):
        result_payload = Signal(object)
        finished_with_results = Signal(object)
        failed = Signal(str)

        def __init__(self, config: dict, stop_event: threading.Event):
            super().__init__()
            self.config = config
            self.stop_event = stop_event
            self.results = []

        def run(self):
            try:
                def forward(payload):
                    self.results.append(payload)
                    self.result_payload.emit(payload)

                run_prediction(self.config, self.stop_event, forward)
                self.finished_with_results.emit(self.results)
            except Exception:
                self.failed.emit(traceback.format_exc())

    class Card(QFrame):
        def __init__(self, title: str = ""):
            super().__init__()
            self.setObjectName("card")
            self.layout = QVBoxLayout(self)
            self.layout.setContentsMargins(16, 14, 16, 16)
            self.layout.setSpacing(10)
            if title:
                label = QLabel(title)
                label.setObjectName("sectionTitle")
                self.layout.addWidget(label)

    class ImageView(QLabel):
        def __init__(self, text: str):
            super().__init__(text)
            self.setObjectName("imageView")
            self.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setMinimumHeight(260)
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self._pixmap: QPixmap | None = None

        def set_pil_image(self, image: Image.Image):
            self._pixmap = pil_to_pixmap(image)
            self._rescale()

        def resizeEvent(self, event):
            super().resizeEvent(event)
            self._rescale()

        def _rescale(self):
            if self._pixmap is None or self.width() <= 0 or self.height() <= 0:
                return
            scaled = self._pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.setPixmap(scaled)

    class WorkbenchWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.settings_service = SettingsService()
            self.settings = self.settings_service.load()
            self.workers: list[Worker] = []
            self.pages: dict[str, QWidget] = {}
            self.training_handle = None
            self.export_handle = None
            self.page_order = ["home", "data", "train", "validate", "settings"]
            self.page_titles = {
                "home": "主页",
                "data": "数据处理",
                "train": "模型训练",
                "validate": "模型验证",
                "settings": "系统设置",
            }
            self.setWindowTitle("YOLO 本地训练工作台")
            self.resize(1100, 780)
            self.setMinimumSize(1100, 780)
            self._build()

        def _build(self):
            root = QWidget()
            root_layout = QVBoxLayout(root)
            root_layout.setContentsMargins(0, 0, 0, 0)
            root_layout.setSpacing(0)

            nav = QFrame()
            nav.setObjectName("nav")
            nav_layout = QHBoxLayout(nav)
            nav_layout.setContentsMargins(22, 14, 22, 14)
            nav_layout.setSpacing(10)
            brand = QLabel("YOLO 本地训练工作台")
            brand.setObjectName("brand")
            nav_layout.addWidget(brand)
            nav_layout.addStretch(1)
            self.nav_buttons = {}
            for key in self.page_order:
                button = QPushButton(self.page_titles[key])
                button.setObjectName("navButton")
                button.setCheckable(True)
                button.clicked.connect(lambda _checked=False, page=key: self.show_page(page))
                nav_layout.addWidget(button)
                self.nav_buttons[key] = button
            root_layout.addWidget(nav)

            self.stack = QStackedWidget()
            self.stack.setObjectName("stack")
            root_layout.addWidget(self.stack, 1)

            self.status = QLabel("就绪")
            self.status.setObjectName("status")
            self.status.setContentsMargins(14, 5, 14, 5)
            root_layout.addWidget(self.status)
            self.setCentralWidget(root)
            self.setStyleSheet(STYLE)
            self.show_page(self.settings["ui"].get("last_page", "home"))

        def show_page(self, key: str):
            if key not in self.page_titles:
                key = "home"
            if key not in self.pages:
                page = self.create_page(key)
                self.pages[key] = page
                self.stack.addWidget(page)
            self.stack.setCurrentWidget(self.pages[key])
            for name, button in self.nav_buttons.items():
                button.setChecked(name == key)
            self.settings["ui"]["last_page"] = key
            self.status.setText(f"当前页面：{self.page_titles[key]}")
            active_page = getattr(self.pages[key], "inner_page", self.pages[key])
            hook = getattr(active_page, "on_show", None)
            if hook:
                hook()

        def create_page(self, key: str):
            if key == "home":
                return HomePage(self)
            if key == "data":
                return scroll_page(DataPage(self))
            if key == "train":
                return scroll_page(TrainPage(self))
            if key == "validate":
                return scroll_page(ValidatePage(self))
            return scroll_page(SettingsPage(self))

        def run_background(self, kind: str, fn):
            worker = Worker(kind, fn)
            self.workers.append(worker)
            worker.finished_with_payload.connect(self.handle_background)
            worker.finished.connect(lambda w=worker: self.workers.remove(w) if w in self.workers else None)
            worker.start()

        def handle_background(self, kind: str, payload):
            if isinstance(payload, dict) and payload.get("error"):
                self.status.setText("后台任务异常")
                QMessageBox.warning(self, "后台任务异常", payload["error"])
                return
            current = self.stack.currentWidget()
            current = getattr(current, "inner_page", current)
            handler = getattr(current, f"apply_{kind}", None)
            if handler:
                handler(payload)

        def closeEvent(self, event):
            self.settings["ui"]["window_width"] = 1100
            self.settings["ui"]["window_height"] = 780
            self.settings_service.save(self.settings)
            stop_process(self.training_handle)
            stop_process(self.export_handle)
            super().closeEvent(event)

    class BasePage(QWidget):
        def __init__(self, app: WorkbenchWindow):
            super().__init__()
            self.app = app

        def page_layout(self):
            layout = QVBoxLayout(self)
            layout.setContentsMargins(16, 16, 16, 16)
            layout.setSpacing(14)
            return layout

        def field(self, label: str, value: str = "", browse=None):
            box = QWidget()
            layout = QVBoxLayout(box)
            layout.setContentsMargins(0, 0, 0, 0)
            caption = QLabel(label)
            caption.setObjectName("fieldLabel")
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            edit = QLineEdit(str(value))
            row.addWidget(edit, 1)
            if browse:
                button = QPushButton("选择")
                button.setObjectName("softButton")
                button.clicked.connect(lambda: browse(edit))
                row.addWidget(button)
            layout.addWidget(caption)
            layout.addLayout(row)
            return box, edit

        def combo_field(self, label: str, value: str, values: list[str]):
            box = QWidget()
            layout = QVBoxLayout(box)
            layout.setContentsMargins(0, 0, 0, 0)
            caption = QLabel(label)
            caption.setObjectName("fieldLabel")
            combo = QComboBox()
            combo.addItems(values)
            if value in values:
                combo.setCurrentText(value)
            layout.addWidget(caption)
            layout.addWidget(combo)
            return box, combo

        def choose_dir(self, edit: QLineEdit):
            path = QFileDialog.getExistingDirectory(self, "选择文件夹", edit.text() or str(ROOT))
            if path:
                edit.setText(path)

        def choose_file(self, edit: QLineEdit, caption: str = "选择文件"):
            path, _ = QFileDialog.getOpenFileName(self, caption, edit.text() or str(ROOT), "All Files (*)")
            if path:
                edit.setText(path)

    def scroll_page(widget: QWidget):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.inner_page = widget  # type: ignore[attr-defined]
        return scroll

    class HomePage(BasePage):
        def __init__(self, app):
            super().__init__(app)
            layout = self.page_layout()
            title = QLabel("欢迎使用 YOLO 本地训练工作台")
            title.setObjectName("pageTitle")
            layout.addWidget(title)
            grid = QGridLayout()
            layout.addLayout(grid, 1)
            self.overview = QTextEdit()
            self.overview.setReadOnly(True)
            overview = Card("项目概览")
            overview.layout.addWidget(self.overview)
            grid.addWidget(overview, 0, 0)
            self.models = QTextEdit()
            self.models.setReadOnly(True)
            models = Card("训练结果模型")
            models.layout.addWidget(self.models)
            grid.addWidget(models, 0, 1)

        def on_show(self):
            paths = self.app.settings["paths"]
            images = Path(paths["images_dir"])
            labels = Path(paths["labels_dir"])
            image_count = len([p for p in images.glob("*") if p.suffix.lower() in IMAGE_SUFFIXES]) if images.exists() else 0
            label_count = len(list(labels.glob("*.txt"))) if labels.exists() else 0
            self.overview.setPlainText(f"项目路径: {self.app.settings['project']['root']}\n图片数量: {image_count}\n标签文件: {label_count}")
            candidates = scan_candidate_models(Path(paths["result_dir"]))
            self.models.setPlainText("\n".join(str(path) for path in candidates[:10]) or "暂无模型")

    class DataPage(BasePage):
        def __init__(self, app):
            super().__init__(app)
            layout = self.page_layout()
            title = QLabel("数据处理")
            title.setObjectName("pageTitle")
            layout.addWidget(title)
            tabs = QTabWidget()
            tabs.addTab(ConvertTab(app), "标注转换")
            tabs.addTab(PreviewTab(app), "标注预览")
            tabs.addTab(RenameTab(app), "批量重命名")
            tabs.addTab(ResizeTab(app), "图片压缩")
            layout.addWidget(tabs, 1)

    class ConvertTab(BasePage):
        def __init__(self, app):
            super().__init__(app)
            layout = QVBoxLayout(self)
            layout.setContentsMargins(12, 12, 12, 12)
            paths = app.settings["paths"]
            dataset = app.settings["dataset"]
            grid = QGridLayout()
            self.images_box, self.images_edit = self.field("图片目录", paths["images_dir"], self.choose_dir)
            self.annotations_box, self.annotations_edit = self.field("Labelme目录", paths["annotations_dir"], self.choose_dir)
            self.output_box, self.output_edit = self.field("输出目录", paths["dataset_dir"], self.choose_dir)
            self.classes_box, self.classes_edit = self.field("类别名称", ",".join(dataset["class_names"]))
            self.task_box, self.task_combo = self.combo_field("任务类型", app.settings["task"]["mode"], ["obb", "detect"])
            ratios = dataset["split_ratios"]
            self.ratio_box, self.ratio_edit = self.field("划分比例", f"{ratios['train']},{ratios['val']},{ratios['test']}")
            self.seed_box, self.seed_edit = self.field("随机种子", str(dataset["random_seed"]))
            self.line_box, self.line_edit = self.field("线宽半径", str(dataset["line_to_obb"]["half_width"]))
            for index, widget in enumerate([self.images_box, self.annotations_box, self.output_box, self.classes_box, self.task_box, self.ratio_box, self.seed_box, self.line_box]):
                grid.addWidget(widget, index // 2, index % 2)
            layout.addLayout(grid)
            actions = QHBoxLayout()
            preview_button = QPushButton("预览转换")
            preview_button.clicked.connect(self.preview)
            run_button = QPushButton("执行转换")
            run_button.clicked.connect(self.run)
            actions.addWidget(preview_button)
            actions.addWidget(run_button)
            actions.addStretch(1)
            layout.addLayout(actions)
            self.log = QTextEdit()
            self.log.setReadOnly(True)
            layout.addWidget(self.log, 1)

        def config(self):
            train, val, test = [float(item.strip()) for item in self.ratio_edit.text().split(",")]
            return ConversionConfig(
                task_mode=self.task_combo.currentText(),
                images_dir=Path(self.images_edit.text()),
                annotations_dir=Path(self.annotations_edit.text()),
                output_dir=Path(self.output_edit.text()),
                labels_dir=Path(self.app.settings["paths"]["labels_dir"]),
                class_names=[item.strip() for item in self.classes_edit.text().split(",") if item.strip()],
                train_ratio=train,
                val_ratio=val,
                test_ratio=test,
                line_to_obb=True,
                line_half_width=float(self.line_edit.text()),
            )

        def preview(self):
            try:
                result = preview_conversion(self.config())
                self.log.setPlainText(f"有标注图片: {result.labeled_count}\n无标注图片: {result.unlabeled_count}\n计划划分: {result.planned_splits}\n未执行任何写入。")
            except Exception as exc:
                self.log.setPlainText(str(exc))

        def run(self):
            try:
                result = run_conversion(self.config())
                self.log.append(f"转换完成: train={result.labeled_train_count}, val={result.labeled_val_count}, test={result.labeled_test_count}, boxes={result.total_boxes}")
            except Exception:
                self.log.append(traceback.format_exc())

    class PreviewTab(BasePage):
        def __init__(self, app):
            super().__init__(app)
            self.preview_items: list[Path] = []
            self.preview_index = 0
            layout = QVBoxLayout(self)
            layout.setContentsMargins(12, 12, 12, 12)
            grid = QGridLayout()
            self.image_box, self.image_edit = self.field("图片文件夹", app.settings["paths"]["images_dir"], self.choose_dir)
            self.label_box, self.label_edit = self.field("标注文件夹", app.settings["paths"]["labels_dir"], self.choose_dir)
            grid.addWidget(self.image_box, 0, 0)
            grid.addWidget(self.label_box, 0, 1)
            layout.addLayout(grid)
            actions = QHBoxLayout()
            for text, slot in [("扫描", self.load_preview_items), ("上一张", self.prev_image), ("下一张", self.next_image)]:
                button = QPushButton(text)
                button.clicked.connect(slot)
                actions.addWidget(button)
            self.current_label = QLabel("等待扫描图片")
            actions.addWidget(self.current_label, 1)
            layout.addLayout(actions)
            images = QHBoxLayout()
            self.source_view = ImageView("原始图片")
            self.result_view = ImageView("标注预览")
            images.addWidget(self.source_view)
            images.addWidget(self.result_view)
            layout.addLayout(images, 1)

        def load_preview_items(self):
            image_dir = Path(self.image_edit.text())
            self.preview_items = sorted(path for path in image_dir.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES) if image_dir.exists() else []
            self.preview_index = 0
            self.render_current()

        def prev_image(self):
            if not self.preview_items:
                self.load_preview_items()
                return
            self.preview_index = (self.preview_index - 1) % len(self.preview_items)
            self.render_current()

        def next_image(self):
            if not self.preview_items:
                self.load_preview_items()
                return
            self.preview_index = (self.preview_index + 1) % len(self.preview_items)
            self.render_current()

        def render_current(self):
            if not self.preview_items:
                self.current_label.setText("未找到图片")
                return
            image_path = self.preview_items[self.preview_index]
            label_path = Path(self.label_edit.text()) / f"{image_path.stem}.txt"
            self.current_label.setText(f"{self.preview_index + 1}/{len(self.preview_items)}  {image_path.name}")
            image = Image.open(image_path).convert("RGB")
            annotations = load_yolo_annotations(image.size, label_path, self.app.settings["task"]["mode"], self.app.settings["dataset"]["class_names"])
            preview = render_annotation_preview(image_path, annotations)
            self.source_view.set_pil_image(image)
            self.result_view.set_pil_image(preview)

    class RenameTab(BasePage):
        def __init__(self, app):
            super().__init__(app)
            self.plan = []
            layout = QVBoxLayout(self)
            layout.setContentsMargins(12, 12, 12, 12)
            grid = QGridLayout()
            self.folder_box, self.folder_edit = self.field("文件夹", app.settings["paths"]["images_dir"], self.choose_dir)
            self.label_box, self.label_edit = self.field("标注文件夹", app.settings["paths"]["labels_dir"], self.choose_dir)
            self.prefix_box, self.prefix_edit = self.field("命名前缀", "A")
            self.start_box, self.start_edit = self.field("起始编号", "1")
            self.padding_box, self.padding_edit = self.field("编号位数", "3")
            for index, widget in enumerate([self.folder_box, self.label_box, self.prefix_box, self.start_box, self.padding_box]):
                grid.addWidget(widget, index // 2, index % 2)
            self.include_labels = QCheckBox("标注文件一并更改")
            self.include_labels.setChecked(True)
            grid.addWidget(self.include_labels, 2, 1)
            layout.addLayout(grid)
            actions = QHBoxLayout()
            preview_button = QPushButton("预览")
            preview_button.clicked.connect(self.preview)
            run_button = QPushButton("执行重命名")
            run_button.clicked.connect(self.run)
            actions.addWidget(preview_button)
            actions.addWidget(run_button)
            actions.addStretch(1)
            layout.addLayout(actions)
            self.table = QTableWidget(0, 5)
            self.table.setHorizontalHeaderLabels(["序号", "原文件名", "新文件名", "图片冲突", "标注状态"])
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            layout.addWidget(self.table, 1)
            for edit in [self.folder_edit, self.label_edit, self.prefix_edit, self.start_edit, self.padding_edit]:
                edit.textChanged.connect(lambda _text: self.preview())
            self.include_labels.stateChanged.connect(lambda _state: self.preview())
            QTimer.singleShot(100, self.preview)

        def preview(self):
            try:
                self.plan = preview_rename(
                    Path(self.folder_edit.text()),
                    self.prefix_edit.text(),
                    int(self.start_edit.text()),
                    int(self.padding_edit.text()),
                    labels_dir=Path(self.label_edit.text()),
                    include_labels=self.include_labels.isChecked(),
                )
            except Exception:
                return
            self.table.setRowCount(len(self.plan))
            for row, item in enumerate(self.plan):
                label_status = item.note or (f"{item.label_source.name} -> {item.label_target.name}" if item.label_source and item.label_target else "不处理")
                values = [item.index, item.old_name, item.new_name, "是" if item.conflict else "无", label_status]
                for column, value in enumerate(values):
                    self.table.setItem(row, column, QTableWidgetItem(str(value)))

        def run(self):
            result = execute_rename(self.plan)
            if result.renamed_count == 0 and result.skipped_count:
                QMessageBox.warning(self, "发现冲突", "检测到标注文件目标名称冲突，已取消本次重命名。")
            else:
                QMessageBox.information(self, "重命名完成", f"已重命名图片 {result.renamed_count} 个，标注 {result.label_renamed_count} 个。")
            self.preview()

    class ResizeTab(BasePage):
        def __init__(self, app):
            super().__init__(app)
            layout = QVBoxLayout(self)
            layout.setContentsMargins(12, 12, 12, 12)
            resize = app.settings["image_resize"]
            grid = QGridLayout()
            self.source_box, self.source_edit = self.field("图片目录", app.settings["paths"]["images_dir"], self.choose_dir)
            self.backup_box, self.backup_edit = self.field("备份目录", resize["backup_dir"], self.choose_dir)
            self.output_box, self.output_edit = self.field("输出目录", resize["output_dir"], self.choose_dir)
            self.long_box, self.long_edit = self.field("长边缩放", str(resize["long_edge"]))
            self.canvas_box, self.canvas_edit = self.field("画布尺寸", str(resize["canvas_size"]))
            self.bg_box, self.bg_combo = self.combo_field("背景颜色", resize["background"], ["white", "black"])
            for index, widget in enumerate([self.source_box, self.backup_box, self.output_box, self.long_box, self.canvas_box, self.bg_box]):
                grid.addWidget(widget, index // 2, index % 2)
            layout.addLayout(grid)
            actions = QHBoxLayout()
            preview_button = QPushButton("预览压缩")
            preview_button.clicked.connect(self.preview)
            run_button = QPushButton("执行压缩")
            run_button.clicked.connect(self.run)
            actions.addWidget(preview_button)
            actions.addWidget(run_button)
            actions.addStretch(1)
            layout.addLayout(actions)
            self.log = QTextEdit()
            self.log.setReadOnly(True)
            layout.addWidget(self.log, 1)

        def config(self):
            return ResizeConfig(
                source_dir=Path(self.source_edit.text()),
                output_dir=Path(self.output_edit.text()),
                backup_dir=Path(self.backup_edit.text()),
                long_edge=int(self.long_edit.text()),
                canvas_size=int(self.canvas_edit.text()),
                background=self.bg_combo.currentText(),
            )

        def preview(self):
            result = preview_resize(self.config())
            self.log.setPlainText(f"计划处理 {len(result.items)} 张图片\n")
            for item in result.items[:80]:
                self.log.append(f"{item.source.name}: {item.original_size} -> {item.resized_size}, scale={item.scale:.3f}")

        def run(self):
            result = run_resize(self.config())
            self.log.append(f"\n压缩完成: {result.processed_count} 张，输出目录: {result.output_dir}")

    class TrainPage(BasePage):
        def __init__(self, app):
            super().__init__(app)
            self.edits = {}
            self.checks = {}
            self.log_queue: Queue | None = None
            self.poll_timer = QTimer(self)
            self.poll_timer.timeout.connect(self.poll_training_queue)
            layout = self.page_layout()
            title = QLabel("模型训练")
            title.setObjectName("pageTitle")
            layout.addWidget(title)
            top = QGridLayout()
            layout.addLayout(top)
            training = self.app.settings["training"]
            fields = ["model_yaml", "pretrained", "data", "project", "base_model", "epochs", "patience", "workers", "batch", "imgsz", "device", "lr"]
            for index, key in enumerate(fields):
                browse = self.choose_file if key in {"model_yaml", "pretrained", "data"} else (self.choose_dir if key == "project" else None)
                box, edit = self.field(key, training.get(key, ""), browse)
                self.edits[key] = edit
                top.addWidget(box, index // 3, index % 3)
            aug = QHBoxLayout()
            for key, label in [("mosaic", "马赛克"), ("fliplr", "左右翻转"), ("flipud", "上下翻转"), ("mixup", "MixUp"), ("scale", "缩放"), ("translate", "平移"), ("degrees", "旋转")]:
                check = QCheckBox(label)
                check.setChecked(float(training.get(key, 0)) > 0)
                self.checks[key] = check
                aug.addWidget(check)
            layout.addLayout(aug)
            actions = QHBoxLayout()
            start = QPushButton("开始训练")
            start.clicked.connect(self.start)
            stop = QPushButton("停止训练")
            stop.setObjectName("softButton")
            stop.clicked.connect(self.stop)
            report = QPushButton("查看模型报告")
            report.setObjectName("softButton")
            report.clicked.connect(self.open_result)
            actions.addWidget(start)
            actions.addWidget(stop)
            actions.addWidget(report)
            self.progress = QProgressBar()
            self.progress.setValue(0)
            actions.addWidget(self.progress, 1)
            layout.addLayout(actions)
            self.log = QTextEdit()
            self.log.setReadOnly(True)
            layout.addWidget(self.log, 1)
            self.refresh_command_preview()

        def collect_config(self):
            config = {key: edit.text() for key, edit in self.edits.items()}
            for key in ("epochs", "patience", "workers", "batch", "imgsz"):
                config[key] = int(config[key])
            config["lr"] = float(config["lr"])
            config["task_mode"] = infer_task_mode_from_model(config.get("model_yaml") or config.get("base_model") or config.get("pretrained"))
            for key, check in self.checks.items():
                config[key] = self.app.settings["training"].get(key, 0) if check.isChecked() else 0
            return config

        def refresh_command_preview(self):
            self.log.setPlainText(" ".join(build_train_command(self.collect_config())) + "\n等待开始训练...")

        def start(self):
            config = self.collect_config()
            command = build_train_command(config)
            self.log.clear()
            self.log.append(" ".join(command))
            self.progress.setValue(0)
            self.log_queue = Queue()
            self.app.training_handle = spawn_logged_process(command, str(ROOT), self.log_queue)
            self.poll_timer.start(150)
            self.app.status.setText("训练中")

        def poll_training_queue(self):
            if self.log_queue is None:
                return
            while not self.log_queue.empty():
                event, payload = self.log_queue.get()
                if event == "log":
                    self.log.append(payload)
                elif event == "exit":
                    self.log.append(f"训练进程结束，退出码：{payload}")
                    self.progress.setValue(100)
                    self.poll_timer.stop()
                    self.app.status.setText("训练结束")

        def stop(self):
            stop_process(self.app.training_handle)
            self.log.append("已请求停止训练。")

        def open_result(self):
            path = Path(self.edits["project"].text())
            if path.exists():
                os.startfile(path)  # type: ignore[attr-defined]

    class ValidatePage(BasePage):
        def __init__(self, app):
            super().__init__(app)
            self.detect_results = []
            self.detect_index = -1
            self.detect_stop = threading.Event()
            self.detect_worker = None
            layout = self.page_layout()
            title = QLabel("模型验证")
            title.setObjectName("pageTitle")
            layout.addWidget(title)
            split = QHBoxLayout()
            layout.addLayout(split, 1)
            left = Card("模型配置 / 检测控制")
            validation = app.settings["validation"]
            self.model_box, self.model_edit = self.field("选择模型", validation["model_path"], lambda edit: self.choose_file(edit, "选择模型"))
            left.layout.addWidget(self.model_box)
            self.mode_box, self.mode_combo = self.combo_field("检测模式", "图片/视频文件夹", ["图片/视频文件夹", "摄像头"])
            left.layout.addWidget(self.mode_box)
            self.source_box, self.source_edit = self.field("输入源", validation["source_path"], self.choose_dir)
            left.layout.addWidget(self.source_box)
            self.camera_box, self.camera_combo = self.combo_field("摄像头", str(validation["camera_index"]), ["0", "1", "2", "3"])
            left.layout.addWidget(self.camera_box)
            self.conf_box, self.conf_edit = self.field("置信度", str(validation["confidence"]))
            self.iou_box, self.iou_edit = self.field("IoU", str(validation["iou"]))
            left.layout.addWidget(self.conf_box)
            left.layout.addWidget(self.iou_box)
            controls = QHBoxLayout()
            start = QPushButton("开始检测")
            start.clicked.connect(self.start_detection)
            stop = QPushButton("停止")
            stop.setObjectName("softButton")
            stop.clicked.connect(self.stop_detection)
            controls.addWidget(start)
            controls.addWidget(stop)
            left.layout.addLayout(controls)
            self.detect_log = QTextEdit()
            self.detect_log.setReadOnly(True)
            left.layout.addWidget(self.detect_log, 1)
            split.addWidget(left, 3)

            right = QVBoxLayout()
            toolbar = QHBoxLayout()
            for text, slot in [("上一张", self.prev_result), ("下一张", self.next_result), ("保存结果", self.save_current_result), ("清空结果", self.clear_results)]:
                button = QPushButton(text)
                button.setObjectName("softButton")
                button.clicked.connect(slot)
                toolbar.addWidget(button)
            self.counter = QLabel("0/0")
            toolbar.addWidget(self.counter)
            toolbar.addStretch(1)
            right.addLayout(toolbar)
            views = QHBoxLayout()
            self.source_view = ImageView("源图")
            self.result_view = ImageView("检测结果图")
            views.addWidget(self.source_view)
            views.addWidget(self.result_view)
            right.addLayout(views, 1)
            self.table = QTableWidget(0, 6)
            self.table.setHorizontalHeaderLabels(["序号", "类别", "置信度", "坐标(x,y)", "尺寸(w×h)", "角度"])
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            right.addWidget(self.table)
            right_widget = QWidget()
            right_widget.setLayout(right)
            split.addWidget(right_widget, 7)
            self.mode_combo.currentTextChanged.connect(self.update_source_mode)
            self.update_source_mode(self.mode_combo.currentText())

        def update_source_mode(self, value):
            camera = value == "摄像头"
            self.source_box.setVisible(not camera)
            self.camera_box.setVisible(camera)

        def on_show(self):
            if not self.model_edit.text():
                self.app.run_background("models", lambda: scan_candidate_models(Path(self.app.settings["paths"]["result_dir"])))

        def apply_models(self, models):
            if models and not self.model_edit.text():
                self.model_edit.setText(str(models[0]))

        def config(self):
            return {
                "model_path": self.model_edit.text(),
                "source_mode": "摄像头" if self.mode_combo.currentText() == "摄像头" else "图片文件夹",
                "source_path": self.source_edit.text(),
                "camera_index": int(self.camera_combo.currentText()),
                "confidence": float(self.conf_edit.text()),
                "iou": float(self.iou_edit.text()),
                "save_dir": self.app.settings["validation"]["save_dir"],
            }

        def start_detection(self):
            self.detect_log.clear()
            self.detect_stop.clear()
            self.detect_results.clear()
            self.detect_index = -1
            self.counter.setText("0/0")
            self.table.setRowCount(0)
            self.app.status.setText("检测中")
            self.detect_worker = DetectionWorker(self.config(), self.detect_stop)
            self.detect_worker.result_payload.connect(self.handle_result)
            self.detect_worker.finished_with_results.connect(self.apply_detect_done)
            self.detect_worker.failed.connect(self.apply_detect_error)
            self.detect_worker.start()

        def apply_detect_done(self, results):
            self.detect_log.append("检测任务结束。")
            self.app.status.setText("检测结束")
            self.detect_worker = None

        def apply_detect_error(self, message):
            self.detect_log.append(message)
            self.app.status.setText("检测异常")
            self.detect_worker = None

        def stop_detection(self):
            self.detect_stop.set()
            self.detect_log.append("已请求停止检测。")

        def handle_result(self, payload):
            self.detect_results.append(payload)
            self.detect_index = len(self.detect_results) - 1
            self.show_detection_payload(payload)

        def show_detection_payload(self, payload):
            self.source_view.set_pil_image(payload["source_image"])
            self.result_view.set_pil_image(payload["result_image"])
            self.table.setRowCount(len(payload["items"]))
            for row, item in enumerate(payload["items"]):
                values = [row + 1, item.label, f"{item.confidence:.3f}", f"({item.center_x:.1f}, {item.center_y:.1f})", f"{item.width:.1f}×{item.height:.1f}", f"{item.angle:.1f}"]
                for column, value in enumerate(values):
                    self.table.setItem(row, column, QTableWidgetItem(str(value)))
            self.counter.setText(f"{self.detect_index + 1}/{len(self.detect_results)}")
            elapsed = payload.get("elapsed", 0.0)
            fps = (1 / elapsed) if elapsed else 0
            self.detect_log.append(f"{payload.get('status')} | 单张耗时: {elapsed * 1000:.1f}ms | FPS: {fps:.1f} | 结果: {len(payload['items'])} 个")

        def prev_result(self):
            if not self.detect_results:
                return
            self.detect_index = (self.detect_index - 1) % len(self.detect_results)
            self.show_detection_payload(self.detect_results[self.detect_index])

        def next_result(self):
            if not self.detect_results:
                return
            self.detect_index = (self.detect_index + 1) % len(self.detect_results)
            self.show_detection_payload(self.detect_results[self.detect_index])

        def save_current_result(self):
            if not self.detect_results or self.detect_index < 0:
                return
            payload = self.detect_results[self.detect_index]
            save_dir = Path(self.app.settings["validation"]["save_dir"])
            save_dir.mkdir(parents=True, exist_ok=True)
            filename = f"gui_result_{self.detect_index + 1:04d}.png"
            payload["result_image"].save(save_dir / filename)
            self.detect_log.append(f"已保存结果: {save_dir / filename}")

        def clear_results(self):
            self.detect_results.clear()
            self.detect_index = -1
            self.counter.setText("0/0")
            self.source_view.clear()
            self.source_view.setText("源图")
            self.result_view.clear()
            self.result_view.setText("检测结果图")
            self.table.setRowCount(0)
            self.detect_log.append("已清空检测结果。")

    class SettingsPage(BasePage):
        def __init__(self, app):
            super().__init__(app)
            layout = self.page_layout()
            title = QLabel("系统设置")
            title.setObjectName("pageTitle")
            layout.addWidget(title)
            self.status_cards = {}
            grid = QGridLayout()
            layout.addLayout(grid)
            for index, label in enumerate(["Pixi", "Torch/CUDA", "GPU", "显存", "CPU", "内存", "磁盘", "模块"]):
                card = Card(label)
                value = QLabel("待检测")
                value.setObjectName("metricValue")
                value.setWordWrap(True)
                card.layout.addWidget(value)
                self.status_cards[label] = value
                grid.addWidget(card, index // 4, index % 4)
            self.log = QTextEdit()
            self.log.setReadOnly(True)
            layout.addWidget(self.log, 1)

        def on_show(self):
            for label in self.status_cards:
                self.set_status_card(label, "检测中...")
            self.log.setPlainText("正在后台检测环境...")
            self.app.run_background(
                "env",
                lambda: {
                    "pixi": pixi_available(),
                    "modules": detect_modules(),
                    "cuda": torch_cuda_summary(),
                    "status": system_status(),
                    "settings": self.app.settings,
                },
            )

        def set_status_card(self, label: str, value: str):
            self.status_cards[label].setText(value)

        def apply_env(self, payload):
            cuda = payload["cuda"]
            status = payload["status"]
            modules = payload["modules"]
            module_summary = " / ".join(f"{name}:{'ok' if ok else '缺失'}" for name, ok in modules.items())
            self.set_status_card("Pixi", "可用" if payload["pixi"] else "不可用")
            self.set_status_card("Torch/CUDA", f"{cuda.get('torch', '未知')} / CUDA {cuda.get('cuda', '未知')}")
            self.set_status_card("GPU", status.get("gpu") or cuda.get("gpu", "待检测"))
            self.set_status_card("显存", status.get("vram", "待检测"))
            self.set_status_card("CPU", status.get("cpu", "待检测"))
            self.set_status_card("内存", status.get("memory", "待检测"))
            self.set_status_card("磁盘", status.get("disk", "待检测"))
            self.set_status_card("模块", module_summary)
            self.log.setPlainText("当前设置:\n" + json.dumps(payload["settings"], ensure_ascii=False, indent=2))

    STYLE = """
    QWidget { font-family: "Microsoft YaHei UI"; font-size: 14px; color: #14233A; }
    #nav { background: #26394D; }
    #brand { color: white; font-size: 24px; font-weight: 700; }
    #navButton { color: white; background: transparent; border: 0; padding: 10px 14px; font-weight: 700; }
    #navButton:checked, #navButton:hover { background: #344D66; border-radius: 6px; }
    #stack { background: #EEF2F6; }
    #status { background: #F7FAFC; color: #627286; }
    #card { background: white; border: 1px solid #D9E3EC; border-radius: 8px; }
    #pageTitle { color: #1A3857; font-size: 28px; font-weight: 700; }
    #sectionTitle { color: #18344F; font-size: 18px; font-weight: 700; }
    #metricValue { color: #0D2B49; font-size: 16px; font-weight: 700; }
    #fieldLabel { color: #627286; font-size: 12px; }
    #imageView { background: #F8FBFD; border: 1px solid #D9E3EC; border-radius: 6px; color: #627286; }
    QLineEdit, QTextEdit, QComboBox, QTableWidget { background: white; border: 1px solid #CFD9E3; border-radius: 5px; padding: 7px; }
    QPushButton { background: #208FD4; color: white; border: 0; border-radius: 5px; padding: 9px 14px; }
    QPushButton#softButton { background: #F5F8FB; color: #14233A; border: 1px solid #D9E3EC; }
    QTabWidget::pane { border: 1px solid #D9E3EC; background: white; border-radius: 6px; }
    QTabBar::tab { padding: 9px 16px; background: #F5F8FB; border: 1px solid #D9E3EC; }
    QTabBar::tab:selected { background: white; color: #208FD4; }
    """

    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei UI", 10))
    window = WorkbenchWindow()
    window.show()
    raise SystemExit(app.exec())
