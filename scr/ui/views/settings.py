from __future__ import annotations

import json

from scr.services.environment_service import detect_modules, pixi_available, system_status, torch_cuda_summary
from scr.ui.page_base import BasePage
from scr.ui.qt import Qt, QFrame, QGridLayout, QLabel, QTextEdit, QTimer, QVBoxLayout

class SettingsPage(BasePage):
    def __init__(self, app):
        super().__init__(app)
        self._refresh_count = 0
        layout = self.page_layout()
        title = QLabel("系统设置")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        cmd_box, self.cmd_dialog_check = self.checkbox_with_help(
            "训练前显示自定义命令框",
            self.app.settings.get("features", {}).get("custom_command_dialog", True),
        )
        self.cmd_dialog_check.setChecked(
            self.app.settings.get("features", {}).get("custom_command_dialog", True)
        )
        self.cmd_dialog_check.stateChanged.connect(self._toggle_custom_cmd)
        layout.addWidget(cmd_box)

        help_box, self.help_icon_check = self.checkbox_with_help(
            "显示配置解释符号",
            self.app.settings.get("features", {}).get("show_help_icons", True),
        )
        self.help_icon_check.setChecked(
            self.app.settings.get("features", {}).get("show_help_icons", True)
        )
        self.help_icon_check.stateChanged.connect(self._toggle_help_icons)
        layout.addWidget(help_box)

        # Task 13: System info - white outer card, gray inner cards
        info_outer = QFrame()
        info_outer.setObjectName("systemInfoOuter")
        info_outer_layout = QGridLayout(info_outer)
        info_outer_layout.setContentsMargins(0, 0, 0, 0)
        info_outer_layout.setSpacing(0)
        info_grid = QGridLayout()
        info_grid.setContentsMargins(12, 12, 12, 12)
        info_grid.setSpacing(8)
        self.status_cards = {}
        for index, label in enumerate(
            ["Pixi", "Torch/CUDA", "GPU", "显存", "CPU", "内存", "磁盘", "模块"]
        ):
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

        self.log = QTextEdit()
        self.prepare_readonly_text(self.log)
        layout.addWidget(self.log, 1)

        # Task 13: Auto-refresh timer every 0.5s
        self._auto_refresh_timer = QTimer(self)
        self._auto_refresh_timer.timeout.connect(self._auto_refresh)
        self._auto_refresh_timer.start(500)

    def _toggle_custom_cmd(self, state):
        self.app.settings.setdefault("features", {})["custom_command_dialog"] = (
            state == Qt.CheckState.Checked.value
        )
        self.app.settings_service.save(self.app.settings)

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

    def _auto_refresh(self):
        self._refresh_count += 1
        self.app.run_background(
            "env_auto",
            lambda: {
                "pixi": pixi_available(),
                "modules": detect_modules(),
                "cuda": torch_cuda_summary(),
                "status": system_status(),
                "settings": self.app.settings,
            },
        )

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
        self._apply_env_data(payload)

    def apply_env_auto(self, payload):
        self._apply_env_data(payload)

    def _apply_env_data(self, payload):
        pixi_text = "可用" if payload.get("pixi") else "不可用"
        modules = payload.get("modules") or {}
        module_text = ", ".join(
            f"{name}:{'OK' if ok else '缺失'}" for name, ok in modules.items()
        ) or "待检测"
        cuda = payload.get("cuda") or {}
        status = payload.get("status") or {}

        self.set_status_card("Pixi", pixi_text)
        self.set_status_card(
            "Torch/CUDA",
            f"{cuda.get('torch', '未知')} / CUDA {cuda.get('cuda', '未知')}",
        )
        self.set_status_card("GPU", status.get("gpu", cuda.get("gpu", "待检测")))
        self.set_status_card("显存", status.get("vram", "待检测"))
        self.set_status_card("CPU", status.get("cpu", "待检测"))
        self.set_status_card("内存", status.get("memory", "待检测"))
        self.set_status_card("磁盘", status.get("disk", "待检测"))
        self.set_status_card("模块", module_text)
        self.log.setPlainText(
            json.dumps(
                {
                    "pixi": payload.get("pixi"),
                    "cuda": cuda,
                    "status": status,
                    "modules": modules,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
