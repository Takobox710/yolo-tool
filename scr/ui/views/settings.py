from __future__ import annotations

from pathlib import Path

from scr.services.settings_service import build_default_settings
from scr.services.environment_service import (
    application_version,
    dependency_versions,
    python_version,
    torch_cuda_summary,
)
from scr.ui.page_base import BasePage
from scr.ui.qt import Qt, QFrame, QGridLayout, QHBoxLayout, QLabel, QMessageBox, QPushButton, QTextEdit, QTimer, QVBoxLayout


STATUS_CARD_LABELS = [
    "Python",
    "Torch",
    "Ultralytics",
    "PySide6",
    "OpenCV",
    "Pillow",
    "psutil",
    "程序版本",
]


class SettingsPage(BasePage):
    def __init__(self, app):
        super().__init__(app)
        self._refresh_count = 0
        layout = self.page_layout()
        title = QLabel("系统设置")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        info_outer = QFrame()
        info_outer.setObjectName("systemInfoOuter")
        info_outer_layout = QGridLayout(info_outer)
        info_outer_layout.setContentsMargins(0, 0, 0, 0)
        info_outer_layout.setSpacing(0)
        info_grid = QGridLayout()
        info_grid.setContentsMargins(12, 12, 12, 12)
        info_grid.setSpacing(8)
        self.status_cards = {}
        for index, label in enumerate(STATUS_CARD_LABELS):
            inner = QFrame()
            inner.setObjectName("systemInfoInner")
            inner_layout = QVBoxLayout(inner)
            inner_layout.setContentsMargins(10, 8, 10, 8)
            lbl = QLabel(label)
            lbl.setObjectName("fieldLabel")
            value = QLabel("待检测")
            value.setObjectName("metricValue")
            value.setWordWrap(True)
            inner_layout.addWidget(lbl)
            inner_layout.addWidget(value)
            self.status_cards[label] = value
            info_grid.addWidget(inner, index // 4, index % 4)
        info_outer_layout.addLayout(info_grid, 0, 0)
        layout.addWidget(info_outer)

        controls_row = QFrame()
        controls_layout = QHBoxLayout(controls_row)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(18)

        dist_box, self.distribution_mode_check = self.checkbox_with_help(
            "多类别分布模式",
            self.app.settings.get("features", {}).get(
                "distribution_multi_class_mode", False
            ),
        )
        self.distribution_mode_check.stateChanged.connect(
            self._toggle_distribution_mode
        )
        controls_layout.addWidget(dist_box)

        cmd_box, self.cmd_dialog_check = self.checkbox_with_help(
            "训练前显示自定义命令框",
            self.app.settings.get("features", {}).get("custom_command_dialog", True),
        )
        self.cmd_dialog_check.setChecked(
            self.app.settings.get("features", {}).get("custom_command_dialog", True)
        )
        self.cmd_dialog_check.stateChanged.connect(self._toggle_custom_cmd)
        controls_layout.addWidget(cmd_box)

        help_box, self.help_icon_check = self.checkbox_with_help(
            "显示配置解释符号",
            self.app.settings.get("features", {}).get("show_help_icons", True),
        )
        self.help_icon_check.setChecked(
            self.app.settings.get("features", {}).get("show_help_icons", True)
        )
        self.help_icon_check.stateChanged.connect(self._toggle_help_icons)
        controls_layout.addWidget(help_box)

        model_box, self.show_last_models_check = self.checkbox_with_help(
            "模型验证显示 last",
            self.app.settings.get("features", {}).get("show_last_training_models", False),
        )
        self.show_last_models_check.setChecked(
            self.app.settings.get("features", {}).get("show_last_training_models", False)
        )
        self.show_last_models_check.stateChanged.connect(
            self._toggle_show_last_training_models
        )
        controls_layout.addWidget(model_box)
        controls_layout.addStretch(1)
        self.reset_btn = QPushButton("恢复默认设置")
        self.reset_btn.setObjectName("softButton")
        self.reset_btn.clicked.connect(self._reset_defaults)
        controls_layout.addWidget(self.reset_btn)
        layout.addWidget(controls_row)

        log_panel = QFrame()
        log_panel.setObjectName("card")
        log_layout = QVBoxLayout(log_panel)
        log_layout.setContentsMargins(12, 10, 12, 12)
        log_layout.setSpacing(8)
        log_title = QLabel("程序日志")
        log_title.setObjectName("sectionTitle")
        log_layout.addWidget(log_title)

        self.log = QTextEdit()
        self.prepare_readonly_text(self.log)
        self.log.setPlainText(self.program_log_text())
        log_layout.addWidget(self.log, 1)
        layout.addWidget(log_panel, 1)
        self.distribution_mode_check.setChecked(
            self.app.settings.get("features", {}).get(
                "distribution_multi_class_mode", False
            )
        )

        self._auto_refresh_timer = QTimer(self)
        self._auto_refresh_timer.timeout.connect(self._auto_refresh)
        self._auto_refresh_timer.setInterval(500)

    def _toggle_custom_cmd(self, state):
        self.app.settings.setdefault("features", {})["custom_command_dialog"] = (
            state == Qt.CheckState.Checked.value
        )
        self.app.settings_service.save(self.app.settings)

    def _toggle_distribution_mode(self, state):
        self.app.settings.setdefault("features", {})[
            "distribution_multi_class_mode"
        ] = state == Qt.CheckState.Checked.value
        self.app.settings_service.save(self.app.settings)
        home_page = self.app.pages.get("home") if hasattr(self.app, "pages") else None
        target = getattr(home_page, "inner_page", home_page)
        hook = getattr(target, "on_show", None)
        if hook:
            hook()

    def _toggle_help_icons(self, state):
        self.app.settings.setdefault("features", {})["show_help_icons"] = (
            state == Qt.CheckState.Checked.value
        )
        self.app.settings_service.save(self.app.settings)
        refresh = getattr(self.app, "refresh_help_icon_visibility", None)
        if refresh:
            refresh()
        else:
            self.refresh_help_icon_visibility()

    def _toggle_show_last_training_models(self, state):
        self.app.settings.setdefault("features", {})["show_last_training_models"] = (
            state == Qt.CheckState.Checked.value
        )
        self.app.settings_service.save(self.app.settings)
        refresh = getattr(self.app, "refresh_validation_model_options", None)
        if refresh:
            refresh()
            return
        pages = getattr(self.app, "pages", {}) or {}
        validate_page = pages.get("validate") if isinstance(pages, dict) else None
        target = getattr(validate_page, "inner_page", validate_page)
        hook = getattr(target, "refresh_model_choices", None)
        if hook:
            hook()

    def _reset_defaults(self):
        answer = QMessageBox.question(
            self,
            "恢复默认设置",
            "将当前项目的设置恢复为默认值？当前项目文件夹路径会保留不变。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        reset = getattr(self.app, "reset_project_settings", None)
        if reset:
            reset("settings")
            return
        reset_settings = getattr(self.app.settings_service, "reset_to_defaults", None)
        if reset_settings:
            self.app.settings = reset_settings()
        else:
            project_root = Path(self.app.settings["project"]["root"])
            self.app.settings = build_default_settings(project_root)
            self.app.settings_service.save(self.app.settings)
        self.cmd_dialog_check.setChecked(
            self.app.settings.get("features", {}).get("custom_command_dialog", True)
        )
        self.distribution_mode_check.setChecked(
            self.app.settings.get("features", {}).get(
                "distribution_multi_class_mode", False
            )
        )
        self.help_icon_check.setChecked(
            self.app.settings.get("features", {}).get("show_help_icons", True)
        )
        self.show_last_models_check.setChecked(
            self.app.settings.get("features", {}).get("show_last_training_models", False)
        )
        refresh = getattr(self.app, "refresh_help_icon_visibility", None)
        if refresh:
            refresh()
        QMessageBox.information(self, "恢复默认设置", "当前项目设置已恢复为默认值。")

    def _auto_refresh(self):
        self._refresh_count += 1
        self.app.run_background(
            "env_auto",
            lambda: self._load_env_payload(),
        )

    def on_show(self):
        if not self._auto_refresh_timer.isActive():
            self._auto_refresh_timer.start()
        for label in self.status_cards:
            self.set_status_card(label, "检测中...")
        self.log.setPlainText(self.program_log_text())
        self.app.run_background(
            "env",
            lambda: self._load_env_payload(),
        )

    def on_hide(self):
        self._auto_refresh_timer.stop()

    def _load_env_payload(self):
        return {
            "python": python_version(),
            "dependencies": dependency_versions(),
            "cuda": torch_cuda_summary(use_subprocess=True),
            "app_version": application_version(),
            "settings": self.app.settings,
        }

    def set_status_card(self, label: str, value: str):
        self.status_cards[label].setText(value)

    def apply_env(self, payload):
        self._apply_env_data(payload)

    def apply_env_auto(self, payload):
        self._apply_env_data(payload)

    def _apply_env_data(self, payload):
        python_text = payload.get("python") or "未知"
        dependencies = payload.get("dependencies") or {}
        cuda = payload.get("cuda") or {}
        torch_text = self._format_torch_status(cuda)

        self.set_status_card("Python", f"{python_text}：可用")
        self.set_status_card("Torch", torch_text)
        self.set_status_card("Ultralytics", self._format_dependency_status(dependencies, "Ultralytics"))
        self.set_status_card("PySide6", self._format_dependency_status(dependencies, "PySide6"))
        self.set_status_card("OpenCV", self._format_dependency_status(dependencies, "OpenCV"))
        self.set_status_card("Pillow", self._format_dependency_status(dependencies, "Pillow"))
        self.set_status_card("psutil", self._format_dependency_status(dependencies, "psutil"))
        self.set_status_card("程序版本", payload.get("app_version", "未知"))

    def append_program_log_entry(self, entry: str) -> None:
        current = self.log.toPlainText().strip()
        if not current or current == "等待程序日志...":
            self.log.setPlainText(entry)
            return
        self.log.append(entry)

    @staticmethod
    def _format_dependency_status(
        dependencies: dict[str, str], label: str
    ) -> str:
        version = str(dependencies.get(label, "未安装"))
        status = "可用" if version not in {"", "未安装"} else "不可用"
        return f"{version}：{status}"

    @staticmethod
    def _format_torch_status(cuda: dict[str, str]) -> str:
        torch_version = str(cuda.get("torch", "未安装"))
        cuda_version = str(cuda.get("cuda", "未知"))
        if torch_version in {"", "未安装", "未知"}:
            return f"{torch_version}：不可用"
        if cuda_version in {"", "None", "未知"}:
            return f"{torch_version}：CUDA不可用"
        return f"{torch_version}：可用"
