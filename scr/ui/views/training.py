from __future__ import annotations

import os
from pathlib import Path
from queue import Queue

from scr.paths import ROOT
from scr.services.environment_service import system_status, torch_cuda_summary
from scr.services.runtime_service import spawn_logged_process, stop_process
from scr.services.settings_service import build_default_settings
from scr.services.training_service import build_train_command, infer_task_mode_from_model
from scr.ui.dialogs import CommandDialog
from scr.ui.helpers import _find_training_model_names, _resolve_training_model_reference
from scr.ui.page_base import BasePage, Card
from scr.ui.qt import QDialog, QGridLayout, QHBoxLayout, QPushButton, QTimer, QTextEdit, QVBoxLayout, QWidget

class TrainPage(BasePage):
    def __init__(self, app):
        super().__init__(app)
        self.edits = {}
        self.checks = {}
        self.metric_labels = {}
        self.log_queue: Queue | None = None
        self.is_training = False
        self.stop_requested = False
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.poll_training_queue)
        self.train_status_timer = QTimer(self)
        self.train_status_timer.timeout.connect(self.refresh_train_status)
        self.train_status_timer.start(500)
        layout = self.page_layout()
        top = QGridLayout()
        top.setColumnStretch(0, 115)
        top.setColumnStretch(1, 85)
        layout.addLayout(top)
        training = self.app.settings["training"]

        left = Card("数据集与增强配置")
        right = Card("训练参数")
        top.addWidget(left, 0, 0)
        top.addWidget(right, 0, 1)

        # Stacked layout: label on top, input + button below
        left_form = QGridLayout()
        left_form.setContentsMargins(0, 0, 0, 0)
        left_form.setHorizontalSpacing(12)
        left_form.setVerticalSpacing(10)
        left.layout.addLayout(left_form)

        # 基础模型 - stacked combo
        current_pretrained = training.get("pretrained", "")
        current_name = Path(current_pretrained).name if current_pretrained else ""
        model_files = _find_training_model_names(
            Path(self.app.settings["project"]["root"])
        )
        base_box, self.pretrained_combo = self.stacked_combo_field(
            "基础模型",
            current_name,
            model_files,
            browse=lambda combo: self._choose_pt_for_combo(combo),
            placeholder="选择或输入 .pt 模型",
        )
        left_form.addWidget(base_box, 0, 0)
        if current_name:
            self.pretrained_combo.setCurrentText(current_name)

        # 数据集YAML
        self.edits["data"], _ = None, None
        data_box, data_edit = self.stacked_path_field(
            "数据集YAML",
            training.get("data", ""),
            self.choose_file,
            "选择训练数据集 data.yaml",
        )
        self.edits["data"] = data_edit
        left_form.addWidget(data_box, 0, 1)

        # 模型YAML (default blank)
        model_yaml_box, model_yaml_edit = self.stacked_path_field(
            "模型YAML",
            training.get("model_yaml", ""),
            self.choose_file,
            "可选，留空使用基础模型",
        )
        self.edits["model_yaml"] = model_yaml_edit
        left_form.addWidget(model_yaml_box, 1, 0)

        # 项目输出
        project_box, project_edit = self.stacked_path_field(
            "项目输出",
            training.get("project", ""),
            self.choose_dir,
            "选择训练结果输出目录",
        )
        self.edits["project"] = project_edit
        left_form.addWidget(project_box, 1, 1)

        # Augmentation checkboxes
        aug = QGridLayout()
        left.layout.addLayout(aug)
        for index, (key, label) in enumerate(
            [
                ("mosaic", "随机拼图"),
                ("scale", "缩放"),
                ("translate", "平移"),
                ("hsv_h", "调色"),
                ("fliplr", "左右翻转"),
                ("flipud", "上下翻转"),
                ("degrees", "旋转"),
                ("mixup", "混合"),
            ]
        ):
            help_text = {
                "mosaic": "随机拼图增强（mosaic）；将多张图随机拼接成一张，增强小目标和复杂场景鲁棒性。",
                "scale": "随机缩放增强（scale）；随机缩放目标与画面，提升对尺寸变化的适应能力。",
                "translate": "随机平移增强（translate）；随机平移图像内容，提升对目标位置变化的适应能力。",
                "hsv_h": "HSV 颜色增强（hsv_h / hsv_s / hsv_v）；同时调节色相、饱和度和明度，提升对光照与色彩变化的适应能力。",
                "fliplr": "左右翻转增强（fliplr）；适合左右方向都合理的场景。",
                "flipud": "上下翻转增强（flipud）；只建议在上下方向同样合理时开启。",
                "degrees": "旋转增强（degrees）；帮助模型适应目标角度变化。",
                "mixup": "MixUp 混合增强（mixup）；将两张图按比例混合，提升泛化能力，但可能拉长收敛时间。",
            }[key]
            box, check = self.checkbox_with_help(
                label, float(training.get(key, 0)) > 0, help_text=help_text
            )
            self.checks[key] = check
            aug.addWidget(box, index // 4, index % 4)

        # Right side: training params
        params = QGridLayout()
        right.layout.addLayout(params)

        # Row 0: optimizer | lr
        optimizer_box, self.optimizer_combo = self.inline_combo_field(
            "优化器",
            training.get("optimizer", "auto"),
            ["auto", "SGD", "Adam", "AdamW", "RMSProp"],
            help_text="训练优化器（optimizer）；用于控制参数更新方式，auto 会交给 Ultralytics 自动决定。",
        )
        current_opt = training.get("optimizer", "auto")
        if current_opt in ["auto", "SGD", "Adam", "AdamW", "RMSProp"]:
            self.optimizer_combo.setCurrentText(current_opt)
        params.addWidget(optimizer_box, 0, 0)

        lr_box, lr_edit = self.inline_field(
            "学习率",
            training.get("lr", ""),
            placeholder="例如 0.001",
            help_text="优化器步长（lr0）；过大可能震荡，过小会收敛变慢。",
        )
        self.edits["lr"] = lr_edit
        params.addWidget(lr_box, 0, 1)

        # Rows 1-3: remaining params, device last (next to 图片尺寸)
        param_order = [
            ("epochs", "训练轮数"),
            ("patience", "早停轮数"),
            ("workers", "线程数"),
            ("batch", "批次大小"),
        ]
        for i, (key, label) in enumerate(param_order):
            placeholder = {
                "epochs": "例如 300",
                "patience": "例如 100",
                "workers": "例如 4",
                "batch": "例如 16",
            }[key]
            help_text = {
                "epochs": "训练轮数（epochs）；设置完整训练的总轮次，更大通常效果更好，但训练耗时更长。",
                "patience": "早停轮数（patience）；连续多轮无提升时自动停止训练，避免无效等待。",
                "workers": "数据加载线程数（workers）；提高后通常更快，但会占用更多 CPU 和系统内存。",
                "batch": "批次大小（batch）；每次迭代送入显存的图片数量，受显存容量限制。",
            }[key]
            box, edit = self.inline_field(
                label,
                training.get(key, ""),
                placeholder=placeholder,
                help_text=help_text,
            )
            self.edits[key] = edit
            params.addWidget(box, 1 + i // 2, i % 2)

        imgsz_box, self.imgsz_combo = self.inline_combo_field(
            "图片尺寸",
            str(training.get("imgsz", 640)),
            ["640", "960", "1280"],
            help_text="训练输入尺寸（imgsz）；更大可能更准，但更吃显存，也会占用更多系统内存和时间。",
            editable=True,
            placeholder="例如 640",
        )
        self.imgsz_combo.setMinimumContentsLength(5)
        params.addWidget(imgsz_box, 3, 0)

        # Device at row 3 col 1, next to 图片尺寸
        self.device_box, self.device_combo = self.inline_combo_field(
            "设备",
            str(training.get("device", "0")),
            ["0", "cpu", "0,1"],
            help_text="训练设备（device）；0 表示首张 GPU，cpu 表示使用处理器，也可填写多个 GPU 编号。",
        )
        params.addWidget(self.device_box, 3, 1)
        actions = QHBoxLayout()
        layout.addLayout(actions)
        control = Card()
        control_body = QGridLayout()
        control.layout.addLayout(control_body)
        self.start_btn = QPushButton("开始训练")
        self.start_btn.clicked.connect(self.start)
        self.stop_btn = QPushButton("停止训练")
        self.stop_btn.setObjectName("softButton")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop)
        report = QPushButton("查看模型报告")
        report.setObjectName("softButton")
        report.clicked.connect(self.open_result)
        control_body.addWidget(self.start_btn, 0, 0, 1, 2)
        control_body.addWidget(self.stop_btn, 1, 0)
        control_body.addWidget(report, 1, 1)
        actions.addWidget(control, 1)

        status = Card()
        status_body = QGridLayout()
        status.layout.addLayout(status_body)
        for index, (key, label) in enumerate(
            [
                ("gpu", "GPU"),
                ("vram", "显存占用"),
                ("cpu", "CPU占用"),
                ("memory", "内存占用"),
            ]
        ):
            card, metric = self.metric_card(label)
            status_body.addWidget(card, 0, index)
            self.metric_labels[key] = metric
        actions.addWidget(status, 3)

        # Task 11: No title, no progress bar - just the log text panel
        log_panel = Card()
        self.log = QTextEdit()
        self.prepare_readonly_text(self.log)
        log_panel.layout.addWidget(self.log, 1)
        layout.addWidget(log_panel, 1)
        self._connect_training_persistence()
        self.refresh_command_preview()

    def on_show(self):
        for metric in self.metric_labels.values():
            metric.setText("检测中...")
        self.refresh_train_status()

    def refresh_train_status(self):
        self.app.run_background(
            "train_status",
            lambda: {"status": system_status(), "cuda": torch_cuda_summary()},
        )

    def apply_train_status(self, payload):
        status = payload["status"]
        cuda = payload["cuda"]
        self.metric_labels["gpu"].setText(
            f"{self.short_gpu_name(status.get('gpu') or cuda.get('gpu', '待检测'))} · {status.get('gpu_usage', '待检测')}"
        )
        self.metric_labels["vram"].setText(status.get("vram", "待检测"))
        self.metric_labels["cpu"].setText(status.get("cpu", "待检测"))
        self.metric_labels["memory"].setText(status.get("memory", "待检测"))

    def collect_config(self):
        config = {}
        config["data"] = (
            self.resolve_path_text(self.edits["data"]) if self.edits["data"] else ""
        )
        config["model_yaml"] = (
            self.resolve_path_text(self.edits["model_yaml"])
            if self.edits["model_yaml"]
            else ""
        )
        config["project"] = (
            self.resolve_path_text(self.edits["project"])
            if self.edits["project"]
            else ""
        )
        config["lr"] = self.edits["lr"].text() if self.edits.get("lr") else "0.001"
        config["epochs"] = (
            self.edits["epochs"].text() if self.edits.get("epochs") else "500"
        )
        config["patience"] = (
            self.edits["patience"].text() if self.edits.get("patience") else "100"
        )
        config["workers"] = (
            self.edits["workers"].text() if self.edits.get("workers") else "2"
        )
        config["batch"] = (
            self.edits["batch"].text() if self.edits.get("batch") else "16"
        )
        config["imgsz"] = self.imgsz_combo.currentText() if hasattr(self, "imgsz_combo") else "640"
        config["device"] = self.device_combo.currentText()
        selected_model = self._resolve_model_reference(
            self.pretrained_combo.currentText()
        )
        config["base_model"] = selected_model
        config["pretrained"] = selected_model
        config["optimizer"] = self.optimizer_combo.currentText()
        for key in ("epochs", "patience", "workers", "batch", "imgsz"):
            try:
                config[key] = int(config[key])
            except (ValueError, TypeError):
                config[key] = int(self.app.settings["training"].get(key, 0))
        try:
            config["lr"] = float(config["lr"])
        except (ValueError, TypeError):
            config["lr"] = float(self.app.settings["training"].get("lr", 0.001))
        config["task_mode"] = infer_task_mode_from_model(
            config.get("model_yaml")
            or config.get("base_model")
            or config.get("pretrained")
        )
        for key, check in self.checks.items():
            if key == "hsv_h":
                continue
            config[key] = (
                self.app.settings["training"].get(
                    key, self._default_training_value(key)
                )
                if check.isChecked()
                else 0
            )
        hsv_enabled = self.checks["hsv_h"].isChecked()
        config["hsv_h"] = (
            self.app.settings["training"].get(
                "hsv_h", self._default_training_value("hsv_h")
            )
            if hsv_enabled
            else 0
        )
        config["hsv_s"] = (
            self.app.settings["training"].get(
                "hsv_s", self._default_training_value("hsv_s")
            )
            if hsv_enabled
            else 0
        )
        config["hsv_v"] = (
            self.app.settings["training"].get(
                "hsv_v", self._default_training_value("hsv_v")
            )
            if hsv_enabled
            else 0
        )
        return config

    def _models_dir(self) -> Path:
        return Path(self.app.settings["paths"]["models_dir"])

    def _default_training_value(self, key: str):
        return build_default_settings(self.project_root())["training"].get(key, 0)

    def _save_training_settings(self, config: dict):
        training = self.app.settings.setdefault("training", {})
        for key in (
            "data",
            "model_yaml",
            "project",
            "lr",
            "epochs",
            "patience",
            "workers",
            "batch",
            "imgsz",
            "device",
            "base_model",
            "pretrained",
            "optimizer",
            "mosaic",
            "fliplr",
            "flipud",
            "mixup",
            "scale",
            "translate",
            "degrees",
            "hsv_h",
            "hsv_s",
            "hsv_v",
        ):
            if key in config:
                training[key] = config[key]
        self.save_settings()

    def _connect_training_persistence(self):
        watched_edits = (
            ("data", self.edits["data"]),
            ("model_yaml", self.edits["model_yaml"]),
            ("project", self.edits["project"]),
            ("lr", self.edits["lr"]),
            ("epochs", self.edits["epochs"]),
            ("patience", self.edits["patience"]),
            ("workers", self.edits["workers"]),
            ("batch", self.edits["batch"]),
        )
        for key, edit in watched_edits:
            edit.textChanged.connect(
                lambda _text, setting_key=key: self._persist_training_text(setting_key)
            )
        self.pretrained_combo.currentTextChanged.connect(self._persist_model_selection)
        self.optimizer_combo.currentTextChanged.connect(
            lambda value: self._persist_training_value("optimizer", value)
        )
        self.imgsz_combo.currentTextChanged.connect(
            lambda value: self._persist_training_value("imgsz", int(value))
        )
        self.device_combo.currentTextChanged.connect(
            lambda value: self._persist_training_value("device", value)
        )
        for key, check in self.checks.items():
            check.toggled.connect(
                lambda _checked, setting_key=key: self._persist_augmentation(setting_key)
            )

    def _persist_training_text(self, key: str):
        edit = self.edits.get(key)
        if edit is None:
            return
        value = self.resolve_path_text(edit) if key in {"data", "model_yaml", "project"} else edit.text()
        self.app.settings.setdefault("training", {})[key] = value
        self.save_settings()
        self.refresh_command_preview()

    def _persist_training_value(self, key: str, value):
        self.app.settings.setdefault("training", {})[key] = value
        self.save_settings()
        self.refresh_command_preview()

    def _persist_model_selection(self, _value: str):
        selected_model = self._resolve_model_reference(self.pretrained_combo.currentText())
        training = self.app.settings.setdefault("training", {})
        training["base_model"] = selected_model
        training["pretrained"] = selected_model
        self.save_settings()
        self.refresh_command_preview()

    def _persist_augmentation(self, key: str):
        training = self.app.settings.setdefault("training", {})
        if key == "hsv_h":
            enabled = self.checks[key].isChecked()
            training["hsv_h"] = (
                training.get("hsv_h", self._default_training_value("hsv_h"))
                if enabled
                else 0
            )
            training["hsv_s"] = (
                training.get("hsv_s", self._default_training_value("hsv_s"))
                if enabled
                else 0
            )
            training["hsv_v"] = (
                training.get("hsv_v", self._default_training_value("hsv_v"))
                if enabled
                else 0
            )
        else:
            training[key] = (
                training.get(key, self._default_training_value(key))
                if self.checks[key].isChecked()
                else 0
            )
        self.save_settings()
        self.refresh_command_preview()

    def _resolve_model_reference(self, model_text: str) -> str:
        return _resolve_training_model_reference(
            model_text,
            Path(self.app.settings["project"]["root"]),
        )

    def refresh_command_preview(self):
        self.log.setPlainText(
            " ".join(build_train_command(self.collect_config()))
            + "\n等待开始训练..."
        )

    def _normalize_command_model_targets(self, command: list[str]) -> list[str]:
        models_dir = self._models_dir()
        models_dir.mkdir(parents=True, exist_ok=True)
        normalized: list[str] = []
        for part in command:
            if not part.startswith(("model=", "pretrained=")):
                normalized.append(part)
                continue
            key, value = part.split("=", 1)
            if not value:
                normalized.append(part)
                continue
            path = Path(value)
            if path.suffix.lower() == ".pt" and not path.is_absolute():
                value = str((models_dir / path.name).resolve())
            normalized.append(f"{key}={value}")
        return normalized

    # Task 9: Only allow one training at a time
    # Task 10: Custom command dialog
    def start(self):
        if self.is_training:
            return
        config = self.collect_config()
        self._save_training_settings(config)
        command = build_train_command(config)
        command = self._normalize_command_model_targets(command)

        # Task 10: Custom command dialog if enabled
        if self.app.settings.get("features", {}).get("custom_command_dialog", True):
            dialog = CommandDialog(command, self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            command = self._normalize_command_model_targets(dialog.get_command())
        else:
            command = self._normalize_command_model_targets(command)

        self.is_training = True
        self.stop_requested = False
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.log.clear()
        self.log.append(" ".join(command))
        self.log_queue = Queue()
        self.app.training_handle = spawn_logged_process(
            command, str(ROOT), self.log_queue
        )
        self.poll_timer.start(150)
        self.app.status.setText("训练中")

    def poll_training_queue(self):
        if self.log_queue is None:
            self._recover_training_state_if_process_exited()
            return
        while not self.log_queue.empty():
            event, payload = self.log_queue.get()
            if event == "log":
                if self.stop_requested:
                    continue
                self.log.append(payload)
            elif event == "exit":
                self._finish_training(payload)
                return
        self._recover_training_state_if_process_exited()

    def stop(self):
        if not self.is_training or self.stop_requested:
            return
        self.stop_requested = True
        self.stop_btn.setEnabled(False)
        self.app.status.setText("停止训练中")
        stop_process(self.app.training_handle)
        self.log.append("已请求停止训练。")

    def _recover_training_state_if_process_exited(self):
        handle = getattr(self.app, "training_handle", None)
        if not self.is_training or handle is None:
            return
        exit_code = handle.process.poll()
        if exit_code is None:
            return
        self._finish_training(exit_code)

    def _finish_training(self, exit_code: int):
        if self.stop_requested:
            self.log.append("训练已停止。")
            self.app.status.setText("训练已停止")
        else:
            self.log.append(f"训练进程结束，退出码：{exit_code}")
            self.app.status.setText("训练结束" if exit_code == 0 else "训练异常结束")
        self.poll_timer.stop()
        self.is_training = False
        self.stop_requested = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.log_queue = None
        self.app.training_handle = None

    def open_result(self):
        path = Path(
            self.resolve_path_text(self.edits["project"])
            if self.edits.get("project")
            else self.app.settings["paths"]["result_dir"]
        )
        if path.exists():
            os.startfile(path)

# ===================================================================
#  Task 14: Validate page - model dropdown, first/last buttons
#  Task 9: Prevent double-start
#  Task 3: Relative paths
# ===================================================================
