from __future__ import annotations

from pathlib import Path

from scr.theme import STYLE
from scr.services.runtime_service import stop_process
from scr.services.settings_service import SettingsService
from scr.ui.qt import QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QStackedWidget, QTimer, QVBoxLayout, QWidget, QIcon
from scr.ui.views.data import DataPage
from scr.ui.views.home import HomePage
from scr.ui.views.settings import SettingsPage
from scr.ui.views.training import TrainPage
from scr.ui.views.validation import ValidatePage
from scr.ui.widgets.base import load_nav_icon, scroll_page
from scr.ui.workers import Worker


class WorkbenchWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings_service = SettingsService()
        self.settings = self.settings_service.load()
        self.settings.setdefault("features", {}).setdefault("custom_command_dialog", True)
        self.settings.setdefault("features", {}).setdefault("show_help_icons", True)
        self.settings.setdefault("training", {}).setdefault("optimizer", "auto")
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
        icon_path = Path(__file__).resolve().parent.parent / "assets" / "app_icon.png"
        if icon_path.exists():
            app_icon = QIcon(str(icon_path))
            self.setWindowIcon(app_icon)
        self.setWindowTitle("YOLO 本地训练工作台")
        self.resize(1100, 770)
        self.setMinimumSize(800, 600)
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
        nav_pix = load_nav_icon()
        if nav_pix is not None:
            icon_label = QLabel()
            icon_label.setPixmap(nav_pix)
            nav_layout.addWidget(icon_label)
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
        self._preload_pages()
        self.show_page("home")

    def _preload_pages(self):
        for key in self.page_order:
            if key in self.pages:
                continue
            page = self.create_page(key)
            self.pages[key] = page
            self.stack.addWidget(page)

    def show_page(self, key: str):
        if key not in self.page_titles:
            key = "home"
        self.dismiss_help_bubbles()
        self.stack.setCurrentWidget(self.pages[key])
        for name, button in self.nav_buttons.items():
            button.setChecked(name == key)
        self.settings["ui"]["last_page"] = key
        self.status.setText(f"当前页面：{self.page_titles[key]}")
        active_page = getattr(self.pages[key], "inner_page", self.pages[key])
        hook = getattr(active_page, "on_show", None)
        if hook:
            QTimer.singleShot(0, hook)

    def create_page(self, key: str):
        if key == "home":
            return scroll_page(HomePage(self))
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

    def refresh_help_icon_visibility(self):
        for page in self.pages.values():
            target = getattr(page, "inner_page", page)
            hook = getattr(target, "refresh_help_icon_visibility", None)
            if hook:
                hook()

    def dismiss_help_bubbles(self):
        for page in self.pages.values():
            target = getattr(page, "inner_page", page)
            hook = getattr(target, "dismiss_help_bubbles", None)
            if hook:
                hook()

    def closeEvent(self, event):
        self.settings["ui"]["window_width"] = 1100
        self.settings["ui"]["window_height"] = 770
        self.settings_service.save(self.settings)
        stop_process(self.training_handle)
        stop_process(self.export_handle)
        super().closeEvent(event)

def build_style() -> str:
    return STYLE
