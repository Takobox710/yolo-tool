from __future__ import annotations

from collections import deque
from pathlib import Path

from src.shared.theme import STYLE
from src.services.settings import SettingsService
from src.services.runtime import stop_process
from src.shared.qt import QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QStackedWidget, QVBoxLayout, QWidget, QIcon, QTimer, Qt
from src.ui.shell.close_guard import confirm_close_if_needed
from src.ui.shell.navigation import ensure_page, reload_pages, show_page
from src.ui.shell.page_registry import PAGE_ORDER, PAGE_TITLES, create_page
from src.ui.shell.program_log import append_program_log, program_log_text, should_log_background_kind
from src.ui.shared.page_base import BasePage
from src.ui.shared.assets import load_app_icon
from src.ui.shared.context import WorkbenchContext
from src.ui.shared.widgets.base import load_nav_icon
from src.ui.shared.workers import Worker


class WorkbenchWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._program_logs: deque[str] = deque(maxlen=600)
        settings_service = SettingsService()
        load_result = settings_service.load()
        self.context = WorkbenchContext(
            settings_service,
            load_result,
            append_log=self.append_program_log,
            program_log=self.program_log_text,
            notify_settings=self.notify_setting_changed,
            run_background=self.run_background,
            switch_project=self.switch_project_root,
            reset_settings=self.reset_project_settings,
            refresh_help_icons=self.refresh_help_icon_visibility,
            refresh_validation_models=self.refresh_validation_model_options,
        )
        self.workers: list[Worker] = []
        self.pages: dict[str, QWidget] = {}
        self.current_page_key = "home"
        self.page_order = list(PAGE_ORDER)
        self.page_titles = dict(PAGE_TITLES)
        self._warmup_page_queue: deque[str] = deque()
        self._page_warmup_timer = QTimer(self)
        self._page_warmup_timer.setSingleShot(True)
        self._page_warmup_timer.timeout.connect(self._warm_up_next_page)
        self._nav_icon_label = None
        self._nav_window_handle = None
        app_icon = load_app_icon()
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)
        self.setWindowTitle("YOLO 本地训练工作台")
        self.resize(1100, 740)
        self.setMinimumSize(800, 600)
        self._build()
        self.append_program_log("程序启动。")

    @property
    def settings_service(self) -> SettingsService:
        return self.context.settings_service

    @property
    def settings(self):
        return self.context.settings

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
        nav_pix = load_nav_icon(self.devicePixelRatioF())
        if nav_pix is not None:
            icon_label = QLabel()
            icon_label.setFixedSize(28, 28)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label.setPixmap(nav_pix)
            nav_layout.addWidget(icon_label)
            self._nav_icon_label = icon_label
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

    def showEvent(self, event):
        super().showEvent(event)
        window_handle = self.windowHandle()
        if window_handle is not None and window_handle is not self._nav_window_handle:
            window_handle.screenChanged.connect(self._refresh_nav_icon)
            self._nav_window_handle = window_handle
        self._refresh_nav_icon()

    def _refresh_nav_icon(self, *_args) -> None:
        if self._nav_icon_label is not None:
            nav_pix = load_nav_icon(self.devicePixelRatioF())
            if nav_pix is not None:
                self._nav_icon_label.setPixmap(nav_pix)
        for child in self.findChildren(QWidget):
            refresh = getattr(child, "refresh_for_device_pixel_ratio", None)
            if refresh:
                refresh()

    def reload_pages(self, current_page: str = "home"):
        reload_pages(self, current_page)
        self._schedule_page_warmup()

    def switch_project_root(self, project_root: str | Path) -> None:
        if self.context.tasks.active():
            answer = QMessageBox.question(
                self,
                "任务正在运行",
                "切换项目会停止当前后台任务，是否继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            self.context.tasks.stop_all()
            self.context.tasks.clear()
        settings_service = SettingsService(project_root=Path(project_root))
        load_result = settings_service.load()
        self.context.replace_settings(settings_service, load_result)
        self.reload_pages("home")
        self.append_program_log(f"已切换项目目录：{self.settings.project.root}")

    def show_page(self, key: str):
        show_page(self, key)

    def create_page(self, key: str):
        return create_page(self, key)

    def ensure_page(self, key: str):
        return ensure_page(self, key)

    def run_background(self, kind: str, fn, *, receiver=None):
        lease = self.context.tasks.begin(kind, generation=self.context.generation)
        if lease is None:
            return None
        if should_log_background_kind(kind):
            self.append_program_log(f"开始后台任务：{kind}")
        worker = Worker(kind, fn)
        self.workers.append(worker)
        worker.finished_with_payload.connect(
            lambda task_kind, payload, target=receiver, task_lease=lease: self.handle_background(
                task_kind, payload, target, task_lease
            )
        )
        worker.finished.connect(
            lambda w=worker, task_lease=lease: self._finish_background(w, task_lease)
        )
        worker.start()

    def _finish_background(self, worker, lease) -> None:
        if worker in self.workers:
            self.workers.remove(worker)
        self.context.tasks.finish(lease)

    def handle_background(self, kind: str, payload, receiver=None, lease=None):
        if lease is not None and not self.context.tasks.is_current(lease):
            return
        if lease is not None and lease.generation != self.context.generation:
            return
        if isinstance(payload, dict) and payload.get("error"):
            self.append_program_log(
                f"后台任务异常（{kind}）：{payload['error']}",
                level="ERROR",
            )
            QMessageBox.warning(self, "后台任务异常", payload["error"])
            return
        if should_log_background_kind(kind):
            self.append_program_log(f"后台任务完成：{kind}")
        current = receiver
        if current is None:
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

    def notify_setting_changed(self, keys: tuple[str, ...], *, source=None):
        """Refresh already-created pages after a setting is edited elsewhere."""
        for page in self.pages.values():
            target = getattr(page, "inner_page", page)
            candidates = [target, *target.findChildren(BasePage)]
            for candidate in candidates:
                if candidate is source:
                    continue
                hook = getattr(candidate, "on_setting_changed", None)
                if hook:
                    hook(keys, None)

    def dismiss_help_bubbles(self):
        for page in self.pages.values():
            target = getattr(page, "inner_page", page)
            hook = getattr(target, "dismiss_help_bubbles", None)
            if hook:
                hook()

    def reset_project_settings(self, current_page: str | None = None):
        target_page = current_page or self.current_page_key
        settings = self.settings_service.reset_to_defaults()
        self.context.replace_settings(
            self.settings_service,
            type(self.context.load_result)(settings=settings, migrated=True),
        )
        self.reload_pages(target_page)
        self.append_program_log("当前项目设置已恢复为默认值。")
        QMessageBox.information(self, "恢复默认设置", "当前项目设置已恢复为默认值。")
        return self.settings

    def closeEvent(self, event):
        self._page_warmup_timer.stop()
        if not confirm_close_if_needed(self):
            event.ignore()
            return
        self.settings.ui.window_width = 1100
        self.settings.ui.window_height = 740
        self.context.save_settings()
        self.context.tasks.stop_all()
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
