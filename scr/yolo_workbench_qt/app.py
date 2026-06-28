from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from scr.yolo_workbench.services.detection_service import scan_candidate_models
from scr.yolo_workbench.services.environment_service import detect_modules, pixi_available, system_status, torch_cuda_summary
from scr.yolo_workbench.services.settings_service import ROOT, SettingsService
from scr.yolo_workbench.services.training_service import build_train_command, infer_task_mode_from_model


def run_app() -> None:
    try:
        from PySide6.QtCore import Qt, QThread, Signal
        from PySide6.QtGui import QFont
        from PySide6.QtWidgets import (
            QApplication,
            QCheckBox,
            QComboBox,
            QFrame,
            QGridLayout,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QMainWindow,
            QPushButton,
            QSizePolicy,
            QStackedWidget,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )
    except ModuleNotFoundError as exc:
        raise SystemExit(f"缺少 Qt 依赖：{exc.name}。请先执行 pixi install 后运行 pixi run app-qt。") from exc

    class Worker(QThread):
        finished_with_payload = Signal(str, object)

        def __init__(self, kind: str, fn):
            super().__init__()
            self.kind = kind
            self.fn = fn

        def run(self):
            self.finished_with_payload.emit(self.kind, self.fn())

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

    class WorkbenchWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.settings_service = SettingsService()
            self.settings = self.settings_service.load()
            self.workers: list[Worker] = []
            self.pages: dict[str, QWidget] = {}
            self.page_order = ["home", "data", "train", "validate", "settings"]
            self.page_titles = {
                "home": "主页",
                "data": "数据处理",
                "train": "模型训练",
                "validate": "模型验证",
                "settings": "系统设置",
            }
            self.setWindowTitle("YOLO 本地训练工作台 Qt")
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
            if key not in self.pages:
                page = self.create_page(key)
                self.pages[key] = page
                self.stack.addWidget(page)
            self.stack.setCurrentWidget(self.pages[key])
            for name, button in self.nav_buttons.items():
                button.setChecked(name == key)
            self.settings["ui"]["last_page"] = key
            self.status.setText(f"当前页面：{self.page_titles[key]}")
            hook = getattr(self.pages[key], "on_show", None)
            if hook:
                hook()

        def create_page(self, key: str):
            if key == "home":
                return HomePage(self)
            if key == "data":
                return DataPage(self)
            if key == "train":
                return TrainPage(self)
            if key == "validate":
                return ValidatePage(self)
            return SettingsPage(self)

        def run_background(self, kind: str, fn):
            worker = Worker(kind, fn)
            self.workers.append(worker)
            worker.finished_with_payload.connect(self.handle_background)
            worker.finished.connect(lambda w=worker: self.workers.remove(w) if w in self.workers else None)
            worker.start()

        def handle_background(self, kind: str, payload):
            current = self.stack.currentWidget()
            handler = getattr(current, f"apply_{kind}", None)
            if handler:
                handler(payload)

        def closeEvent(self, event):
            self.settings["ui"]["window_width"] = 1100
            self.settings["ui"]["window_height"] = 780
            self.settings_service.save(self.settings)
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

        def field(self, label: str, value: str = ""):
            box = QWidget()
            layout = QVBoxLayout(box)
            layout.setContentsMargins(0, 0, 0, 0)
            caption = QLabel(label)
            caption.setObjectName("fieldLabel")
            edit = QLineEdit(str(value))
            layout.addWidget(caption)
            layout.addWidget(edit)
            return box, edit

    class HomePage(BasePage):
        def __init__(self, app):
            super().__init__(app)
            layout = self.page_layout()
            title = QLabel("欢迎使用 YOLO 本地训练工作台")
            title.setObjectName("pageTitle")
            layout.addWidget(title)
            grid = QGridLayout()
            layout.addLayout(grid, 1)
            overview = Card("项目概览")
            self.overview = QTextEdit()
            self.overview.setReadOnly(True)
            overview.layout.addWidget(self.overview)
            grid.addWidget(overview, 0, 0)
            models = Card("训练结果模型")
            self.models = QTextEdit()
            self.models.setReadOnly(True)
            models.layout.addWidget(self.models)
            grid.addWidget(models, 0, 1)

        def on_show(self):
            paths = self.app.settings["paths"]
            images = Path(paths["images_dir"])
            labels = Path(paths["labels_dir"])
            image_count = len([p for p in images.glob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}]) if images.exists() else 0
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
            row = QHBoxLayout()
            layout.addLayout(row, 1)
            for name in ["标注转换", "标注预览", "批量重命名", "图片压缩"]:
                card = Card(name)
                card.layout.addWidget(QLabel("Qt 版本已接入页面框架，业务按钮将继续复用现有服务层迁移。"))
                row.addWidget(card)

    class TrainPage(BasePage):
        def __init__(self, app):
            super().__init__(app)
            self.edits = {}
            layout = self.page_layout()
            title = QLabel("模型训练")
            title.setObjectName("pageTitle")
            layout.addWidget(title)
            grid = QGridLayout()
            layout.addLayout(grid)
            training = self.app.settings["training"]
            for index, key in enumerate(["model_yaml", "data", "project", "epochs", "batch", "imgsz", "device", "lr"]):
                box, edit = self.field(key, training.get(key, ""))
                self.edits[key] = edit
                grid.addWidget(box, index // 2, index % 2)
            self.command = QTextEdit()
            self.command.setReadOnly(True)
            layout.addWidget(self.command, 1)
            actions = QHBoxLayout()
            build = QPushButton("生成训练命令")
            build.clicked.connect(self.refresh_command)
            actions.addWidget(build)
            actions.addStretch(1)
            layout.addLayout(actions)
            self.refresh_command()

        def refresh_command(self):
            config = {key: edit.text() for key, edit in self.edits.items()}
            for key in ("epochs", "batch", "imgsz"):
                config[key] = int(config[key] or 0)
            config["lr"] = float(config["lr"] or 0)
            config["task_mode"] = infer_task_mode_from_model(config.get("model_yaml"))
            self.command.setPlainText(" ".join(build_train_command(config)))

    class ValidatePage(BasePage):
        def __init__(self, app):
            super().__init__(app)
            layout = self.page_layout()
            title = QLabel("模型验证")
            title.setObjectName("pageTitle")
            layout.addWidget(title)
            split = QHBoxLayout()
            layout.addLayout(split, 1)
            left = Card("模型配置")
            self.model_combo = QComboBox()
            left.layout.addWidget(self.model_combo)
            self.mode_combo = QComboBox()
            self.mode_combo.addItems(["图片/视频文件夹", "摄像头"])
            left.layout.addWidget(self.mode_combo)
            split.addWidget(left, 3)
            right = Card("检测结果")
            right.layout.addWidget(QLabel("Qt 页面栈已就绪，后续迁移图像预览和结果表。"))
            split.addWidget(right, 7)

        def on_show(self):
            if self.model_combo.count() == 0:
                self.app.run_background("models", lambda: scan_candidate_models(Path(self.app.settings["paths"]["result_dir"])))

        def apply_models(self, models):
            self.model_combo.clear()
            self.model_combo.addItems([str(path) for path in models] or ["未找到模型"])

    class SettingsPage(BasePage):
        def __init__(self, app):
            super().__init__(app)
            layout = self.page_layout()
            title = QLabel("系统设置")
            title.setObjectName("pageTitle")
            layout.addWidget(title)
            self.log = QTextEdit()
            self.log.setReadOnly(True)
            layout.addWidget(self.log, 1)

        def on_show(self):
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

        def apply_env(self, payload):
            self.log.setPlainText(json.dumps(payload, ensure_ascii=False, indent=2))

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
    #fieldLabel { color: #627286; font-size: 12px; }
    QLineEdit, QTextEdit, QComboBox { background: white; border: 1px solid #CFD9E3; border-radius: 5px; padding: 7px; }
    QPushButton { background: #208FD4; color: white; border: 0; border-radius: 5px; padding: 9px 14px; }
    """

    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei UI", 10))
    window = WorkbenchWindow()
    window.show()
    raise SystemExit(app.exec())
