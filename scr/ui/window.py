from __future__ import annotations

from collections import deque
from datetime import datetime
from pathlib import Path

from scr.theme import STYLE
from scr.services.runtime_service import stop_process
from scr.services.settings_service import SettingsService
from scr.ui.qt import QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QStackedWidget, QTimer, QVBoxLayout, QWidget, QIcon
from scr.ui.views.annotation import AnnotationPage
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
        self._apply_settings_defaults()
        self.workers: list[Worker] = []
        self.pages: dict[str, QWidget] = {}
        self.training_handle = None
        self.export_handle = None
        self.validation_handle = None
        self._program_logs: deque[str] = deque(maxlen=600)
        self.current_page_key = "home"
        self.page_order = ["home", "annotation", "data", "train", "validate", "settings"]
        self.page_titles = {
            "home": "主页",
            "annotation": "数据标注",
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
        self.resize(1100, 740)
        self.setMinimumSize(800, 600)
        self._build()
        self.append_program_log("程序启动。")

    def _apply_settings_defaults(self) -> None:
        self.settings.setdefault("features", {}).setdefault("custom_command_dialog", True)
        self.settings.setdefault("features", {}).setdefault("show_help_icons", True)
        self.settings.setdefault("features", {}).setdefault("show_last_training_models", False)
        self.settings.setdefault("training", {}).setdefault("optimizer", "auto")

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

    def _clear_pages(self):
        while self.stack.count():
            widget = self.stack.widget(0)
            self.stack.removeWidget(widget)
            widget.setParent(None)
        self.pages.clear()

    def reload_pages(self, current_page: str = "home"):
        self._clear_pages()
        self._preload_pages()
        self.show_page(current_page)

    def switch_project_root(self, project_root: str | Path) -> None:
        self.settings_service = SettingsService(project_root=Path(project_root))
        self.settings = self.settings_service.load()
        self._apply_settings_defaults()
        self.reload_pages("home")
        self.append_program_log(f"已切换项目目录：{self.settings['project']['root']}")

    def show_page(self, key: str):
        if key not in self.page_titles:
            key = "home"
        previous_page = self.pages.get(self.current_page_key)
        if previous_page is not None and self.current_page_key != key:
            self._invoke_page_hook(previous_page, "on_hide")
        self.current_page_key = key
        self.dismiss_help_bubbles()
        self.stack.setCurrentWidget(self.pages[key])
        for name, button in self.nav_buttons.items():
            button.setChecked(name == key)
        self.settings["ui"]["last_page"] = key
        QTimer.singleShot(0, lambda: self._invoke_page_hook(self.pages[key], "on_show"))

    def create_page(self, key: str):
        if key == "home":
            return scroll_page(HomePage(self))
        if key == "annotation":
            return AnnotationPage(self)
        if key == "data":
            return scroll_page(DataPage(self))
        if key == "train":
            return scroll_page(TrainPage(self))
        if key == "validate":
            return scroll_page(ValidatePage(self))
        return scroll_page(SettingsPage(self))

    def run_background(self, kind: str, fn):
        if self._should_log_background_kind(kind):
            self.append_program_log(f"开始后台任务：{kind}")
        worker = Worker(kind, fn)
        self.workers.append(worker)
        worker.finished_with_payload.connect(self.handle_background)
        worker.finished.connect(lambda w=worker: self.workers.remove(w) if w in self.workers else None)
        worker.start()

    def handle_background(self, kind: str, payload):
        if isinstance(payload, dict) and payload.get("error"):
            self.append_program_log(
                f"后台任务异常（{kind}）：{payload['error']}",
                level="ERROR",
            )
            QMessageBox.warning(self, "后台任务异常", payload["error"])
            return
        if self._should_log_background_kind(kind):
            self.append_program_log(f"后台任务完成：{kind}")
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

    def refresh_validation_model_options(self):
        for page in self.pages.values():
            target = getattr(page, "inner_page", page)
            hook = getattr(target, "refresh_model_choices", None)
            if hook:
                hook()

    def dismiss_help_bubbles(self):
        for page in self.pages.values():
            target = getattr(page, "inner_page", page)
            hook = getattr(target, "dismiss_help_bubbles", None)
            if hook:
                hook()

    def reset_project_settings(self, current_page: str | None = None) -> dict:
        target_page = current_page or self.current_page_key
        self.settings = self.settings_service.reset_to_defaults()
        self._apply_settings_defaults()
        self.reload_pages(target_page)
        self.append_program_log("当前项目设置已恢复为默认值。")
        QMessageBox.information(self, "恢复默认设置", "当前项目设置已恢复为默认值。")
        return self.settings

    def closeEvent(self, event):
        self.settings["ui"]["window_width"] = 1100
        self.settings["ui"]["window_height"] = 740
        self.settings_service.save(self.settings)
        stop_process(self.training_handle)
        stop_process(self.export_handle)
        stop_process(self.validation_handle)
        super().closeEvent(event)

    def _invoke_page_hook(self, page: QWidget, hook_name: str):
        target = getattr(page, "inner_page", page)
        hook = getattr(target, hook_name, None)
        if hook:
            hook()

    def append_program_log(self, message: str, *, level: str = "INFO") -> None:
        text = str(message or "").strip()
        if not text:
            return
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] [{level}] {text}"
        self._program_logs.append(entry)
        settings_page = self.pages.get("settings")
        target = getattr(settings_page, "inner_page", settings_page)
        hook = getattr(target, "append_program_log_entry", None)
        if callable(hook):
            hook(entry)

    def program_log_text(self) -> str:
        if not self._program_logs:
            return "等待程序日志..."
        return "\n".join(self._program_logs)

    @staticmethod
    def _should_log_background_kind(kind: str) -> bool:
        return kind not in {"env", "env_auto", "train_status"}

def build_style() -> str:
    return STYLE
