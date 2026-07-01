from __future__ import annotations

import os
from pathlib import Path
from queue import Queue

from scr.paths import ROOT
from scr.services.environment_service import system_status, torch_cuda_summary
from scr.services.runtime_service import spawn_logged_process, stop_process
from scr.services.training_service import build_train_command, infer_task_mode_from_model
from scr.ui.dialogs import CommandDialog
from scr.ui.helpers import _find_pt_files_in_data_models
from scr.ui.page_base import BasePage, Card
from scr.ui.qt import QCheckBox, QComboBox, QDialog, QGridLayout, QHBoxLayout, QLabel, QPushButton, QTimer, QTextEdit, QVBoxLayout, QWidget

class TrainPage(BasePage):
    def __init__(self, app):
        super().__init__(app)
        self.edits = {}
        self.checks = {}
        self.metric_labels = {}
        self.log_queue: Queue | None = None
        self.is_training = False
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
        model_files = _find_pt_files_in_data_models(
            Path(self.app.settings["project"]["root"])
        )
        current_pretrained = training.get("pretrained", "")
        current_name = Path(current_pretrained).name if current_pretrained else ""
        base_box, self.pretrained_combo = self.stacked_combo_field(
            "基础模型",
            current_name,
            model_files,
            browse=lambda combo: self._choose_pt_for_combo(combo),
            placeholder="选择或输入 .pt 模型",
        )
        left_form.addWidget(base_box, 0, 0)

        # 数据集YAML
        self.edits["data"], _ = None, None
        data_box, data_edit = self.stacked_path_field(
            "数据集YAML",
            training.get("data", ""),
            self.choose_file,
            "选择 data.yaml",
        )
        self.edits["data"] = data_edit
        left_form.addWidget(data_box, 0, 1)

        # 模型YAML (default blank)
        model_yaml_box, model_yaml_edit = self.stacked_path_field(
            "模型YAML", "", self.choose_file, "可选，留空使用基础模型"
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
                ("mosaic", "马赛克"),
                ("scale", "缩放"),
                ("translate", "平移"),
                ("hsv_h", "HSV"),
                ("fliplr", "左右翻转"),
                ("flipud", "上下翻转"),
                ("degrees", "旋转"),
                ("mixup", "MixUp"),
            ]
        ):
            check = QCheckBox(label)
            check.setChecked(float(training.get(key, 0)) > 0)
            self.checks[key] = check
            aug.addWidget(check, index // 4, index % 4)

        # Right side: training params
        params = QGridLayout()
        right.layout.addLayout(params)

        # Row 0: optimizer | lr
        optimizer_box = QWidget()
        optimizer_layout = QHBoxLayout(optimizer_box)
        optimizer_layout.setContentsMargins(0, 0, 0, 0)
        opt_label = QLabel("优化器")
        opt_label.setObjectName("inlineFieldLabel")
        opt_label.setFixedWidth(88)
        self.optimizer_combo = QComboBox()
        self.optimizer_combo.addItems(["auto", "SGD", "Adam", "AdamW", "RMSProp"])
        current_opt = training.get("optimizer", "auto")
        if current_opt in ["auto", "SGD", "Adam", "AdamW", "RMSProp"]:
            self.optimizer_combo.setCurrentText(current_opt)
        optimizer_layout.addWidget(opt_label)
        optimizer_layout.addWidget(self.optimizer_combo, 1)
        params.addWidget(optimizer_box, 0, 0)

        lr_box, lr_edit = self.inline_field("学习率", training.get("lr", ""))
        self.edits["lr"] = lr_edit
        params.addWidget(lr_box, 0, 1)

        # Rows 1-3: remaining params, device last (next to 图片尺寸)
        param_order = [
            ("epochs", "Epochs"),
            ("patience", "Patience"),
            ("workers", "Workers"),
            ("batch", "Batch"),
            ("imgsz", "图片尺寸"),
        ]
        for i, (key, label) in enumerate(param_order):
            box, edit = self.inline_field(label, training.get(key, ""))
            self.edits[key] = edit
            params.addWidget(box, 1 + i // 2, i % 2)

        # Device at row 3 col 1, next to 图片尺寸
        self.device_box, self.device_combo = self.inline_combo_field(
            "设备", str(training.get("device", "0")), ["0", "cpu", "0,1"]
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
        self.log.setReadOnly(True)
        log_panel.layout.addWidget(self.log, 1)
        layout.addWidget(log_panel, 1)
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
            self.edits["epochs"].text() if self.edits.get("epochs") else "800"
        )
        config["patience"] = (
            self.edits["patience"].text() if self.edits.get("patience") else "150"
        )
        config["workers"] = (
            self.edits["workers"].text() if self.edits.get("workers") else "2"
        )
        config["batch"] = (
            self.edits["batch"].text() if self.edits.get("batch") else "16"
        )
        config["imgsz"] = (
            self.edits["imgsz"].text() if self.edits.get("imgsz") else "640"
        )
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
                self.app.settings["training"].get(key, 0)
                if check.isChecked()
                else 0
            )
        hsv_enabled = self.checks["hsv_h"].isChecked()
        config["hsv_h"] = (
            self.app.settings["training"].get("hsv_h", 0) if hsv_enabled else 0
        )
        config["hsv_s"] = (
            self.app.settings["training"].get("hsv_s", 0) if hsv_enabled else 0
        )
        config["hsv_v"] = (
            self.app.settings["training"].get("hsv_v", 0) if hsv_enabled else 0
        )
        return config

    def _resolve_model_reference(self, model_text: str) -> str:
        model_text = str(model_text or "").strip()
        if not model_text:
            return ""
        model_path = Path(model_text)
        if model_path.is_absolute() and model_path.exists():
            return str(model_path.resolve())
        project_root = Path(self.app.settings["project"]["root"])
        for candidate in (
            project_root / model_text,
            project_root / "data" / "models" / model_text,
        ):
            if candidate.exists():
                return str(candidate.resolve())
        return model_text

    def refresh_command_preview(self):
        self.log.setPlainText(
            " ".join(build_train_command(self.collect_config()))
            + "\n等待开始训练..."
        )

    # Task 9: Only allow one training at a time
    # Task 10: Custom command dialog
    def start(self):
        if self.is_training:
            return
        config = self.collect_config()
        command = build_train_command(config)

        # Task 10: Custom command dialog if enabled
        if self.app.settings.get("features", {}).get("custom_command_dialog", True):
            dialog = CommandDialog(command, self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            command = dialog.get_command()

        self.is_training = True
        self.start_btn.setEnabled(False)
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
            return
        while not self.log_queue.empty():
            event, payload = self.log_queue.get()
            if event == "log":
                self.log.append(payload)
            elif event == "exit":
                self.log.append(f"训练进程结束，退出码：{payload}")
                self.poll_timer.stop()
                self.is_training = False
                self.start_btn.setEnabled(True)
                self.app.status.setText("训练结束")

    def stop(self):
        stop_process(self.app.training_handle)
        self.log.append("已请求停止训练。")

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
