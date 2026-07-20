from __future__ import annotations

from collections import deque
from pathlib import Path

from src.shared.paths import ICON_PNG
from src.shared.theme import STYLE
from src.services.runtime import stop_process
from src.services.settings import SettingsService
from src.shared.qt import QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QStackedWidget, QVBoxLayout, QWidget, QIcon, QTimer
from src.ui.shell.close_guard import confirm_close_if_needed
from src.ui.shell.navigation import ensure_page, reload_pages, show_page
from src.ui.shell.page_registry import PAGE_ORDER, PAGE_TITLES, create_page
from src.ui.shell.program_log import append_program_log, program_log_text, should_log_background_kind
from src.ui.shared.page_base import BasePage
from src.ui.shared.widgets.base import load_nav_icon
from src.ui.shared.workers import Worker


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
        self.page_order = list(PAGE_ORDER)
        self.page_titles = dict(PAGE_TITLES)
        self._warmup_page_queue: deque[str] = deque()
        self._page_warmup_timer = QTimer(self)
        self._page_warmup_timer.setSingleShot(True)
        self._page_warmup_timer.timeout.connect(self._warm_up_next_page)
        if ICON_PNG.exists():
            app_icon = QIcon(str(ICON_PNG))
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
        show_page(self, "home")
        self._schedule_page_warmup()

    def reload_pages(self, current_page: str = "home"):
        reload_pages(self, current_page)
        self._schedule_page_warmup()

    def switch_project_root(self, project_root: str | Path) -> None:
        self.settings_service = SettingsService(project_root=Path(project_root))
        self.settings = self.settings_service.load()
        self._apply_settings_defaults()
        self.reload_pages("home")
        self.append_program_log(f"已切换项目目录：{self.settings['project']['root']}")

    def show_page(self, key: str):
        show_page(self, key)

    def create_page(self, key: str):
        return create_page(self, key)

    def ensure_page(self, key: str):
        return ensure_page(self, key)

    def run_background(self, kind: str, fn):
        if should_log_background_kind(kind):
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
        if should_log_background_kind(kind):
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

    def notify_setting_changed(self, keys: tuple[str, ...], value, *, source=None):
        """Refresh already-created pages after a setting is edited elsewhere."""
        for page in self.pages.values():
            target = getattr(page, "inner_page", page)
            candidates = [target, *target.findChildren(BasePage)]
            for candidate in candidates:
                if candidate is source:
                    continue
                hook = getattr(candidate, "on_setting_changed", None)
                if hook:
                    hook(keys, value)

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
        self._page_warmup_timer.stop()
        if not confirm_close_if_needed(self):
            event.ignore()
            return
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
        append_program_log(self, message, level=level)

    def program_log_text(self) -> str:
        return program_log_text(self)

    def _schedule_page_warmup(self) -> None:
        self._page_warmup_timer.stop()
        self._warmup_page_queue = deque(
            key for key in self.page_order if key != "home" and key not in self.pages
        )
        if self._warmup_page_queue:
            self._page_warmup_timer.start(0)

    def _warm_up_next_page(self) -> None:
        if not self.isVisible():
            if self._warmup_page_queue:
                self._page_warmup_timer.start(50)
            return
        while self._warmup_page_queue:
            key = self._warmup_page_queue.popleft()
            if key in self.pages:
                continue
            page = self.ensure_page(key)
            self._invoke_page_hook(page, "prepare_for_first_show")
            break
        if self._warmup_page_queue:
            self._page_warmup_timer.start(0)

def build_style() -> str:
    return STYLE


