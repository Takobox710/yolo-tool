from __future__ import annotations

from pathlib import Path

from src.services.training import find_training_model_names
from src.ui.shared.page_base import Card
from src.shared.qt import QGridLayout, QHBoxLayout, QPushButton, QTextEdit


def build_training_layout(page) -> None:
    layout = page.page_layout()
    top = QGridLayout()
    top.setColumnStretch(0, 115)
    top.setColumnStretch(1, 85)
    layout.addLayout(top)
    training = page.app.settings["training"]

    left = Card("数据集与增强配置")
    right = Card("训练参数")
    top.addWidget(left, 0, 0)
    top.addWidget(right, 0, 1)

    left_form = QGridLayout()
    left_form.setContentsMargins(0, 0, 0, 0)
    left_form.setHorizontalSpacing(12)
    left_form.setVerticalSpacing(10)
    left.layout.addLayout(left_form)

    current_pretrained = training.get("pretrained", "")
    current_name = Path(current_pretrained).name if current_pretrained else ""
    model_files = find_training_model_names(
        Path(page.app.settings["project"]["root"])
    )
    base_box, page.pretrained_combo = page.stacked_combo_field(
        "基础模型",
        current_name,
        model_files,
        browse=lambda combo: page._choose_pt_for_combo(combo),
        placeholder="选择或输入 .pt 模型",
    )
    left_form.addWidget(base_box, 0, 0)
    if current_name:
        page.pretrained_combo.setCurrentText(current_name)

    page.edits["data"], _ = None, None
    data_box, data_edit = page.stacked_path_field(
        "数据集YAML",
        training.get("data", ""),
        page.choose_file,
        "选择训练数据集 data.yaml",
    )
    page.edits["data"] = data_edit
    left_form.addWidget(data_box, 0, 1)

    model_yaml_box, model_yaml_edit = page.stacked_path_field(
        "模型YAML",
        training.get("model_yaml", ""),
        page.choose_file,
        "可选，留空使用基础模型",
    )
    page.edits["model_yaml"] = model_yaml_edit
    left_form.addWidget(model_yaml_box, 1, 0)

    project_box, project_edit = page.stacked_path_field(
        "项目输出",
        training.get("project", ""),
        page.choose_dir,
        "选择训练结果输出目录",
    )
    page.edits["project"] = project_edit
    left_form.addWidget(project_box, 1, 1)

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
        box, check = page.checkbox_with_help(
            label, float(training.get(key, 0)) > 0, help_text=help_text
        )
        page.checks[key] = check
        aug.addWidget(box, index // 4, index % 4)

    params = QGridLayout()
    params.setHorizontalSpacing(30)
    right.layout.addLayout(params)

    optimizer_box, page.optimizer_combo = page.inline_combo_field(
        "优化器",
        training.get("optimizer", "auto"),
        ["auto", "SGD", "Adam", "AdamW", "RMSProp"],
        help_text="训练优化器（optimizer）；用于控制参数更新方式，auto 会交给 Ultralytics 自动决定。",
        label_width=80,
    )
    current_opt = training.get("optimizer", "auto")
    if current_opt in ["auto", "SGD", "Adam", "AdamW", "RMSProp"]:
        page.optimizer_combo.setCurrentText(current_opt)
    params.addWidget(optimizer_box, 0, 0)

    lr_box, lr_edit = page.inline_field(
        "学习率",
        training.get("lr", ""),
        placeholder="例如 0.001",
        help_text="优化器步长（lr0）；过大可能震荡，过小会收敛变慢。",
        label_width=80,
    )
    page.edits["lr"] = lr_edit
    params.addWidget(lr_box, 0, 1)

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
        box, edit = page.inline_field(
            label,
            training.get(key, ""),
            placeholder=placeholder,
            help_text=help_text,
            label_width=80,
        )
        page.edits[key] = edit
        params.addWidget(box, 1 + i // 2, i % 2)

    imgsz_box, page.imgsz_combo = page.inline_combo_field(
        "图片尺寸",
        str(training.get("imgsz", 640)),
        ["640", "960", "1280"],
        help_text="训练输入尺寸（imgsz）；更大可能更准，但更吃显存，也会占用更多系统内存和时间。",
        editable=True,
        placeholder="例如 640",
        label_width=80,
    )
    page.imgsz_combo.setMinimumContentsLength(5)
    params.addWidget(imgsz_box, 3, 0)

    page.device_box, page.device_combo = page.inline_combo_field(
        "设备",
        str(training.get("device", "0")),
        ["0", "cpu", "0,1"],
        help_text="训练设备（device）；0 表示首张 GPU，cpu 表示使用处理器，也可填写多个 GPU 编号。",
        label_width=80,
    )
    params.addWidget(page.device_box, 3, 1)

    actions = QHBoxLayout()
    layout.addLayout(actions)
    control = Card()
    control_body = QGridLayout()
    control.layout.addLayout(control_body)
    page.start_btn = QPushButton("开始训练")
    page.start_btn.clicked.connect(page.start)
    page.stop_btn = QPushButton("停止训练")
    page.stop_btn.setObjectName("softButton")
    page.stop_btn.setEnabled(False)
    page.stop_btn.clicked.connect(page.stop)
    report = QPushButton("查看模型报告")
    report.setObjectName("softButton")
    report.clicked.connect(page.open_result)
    control_body.addWidget(page.start_btn, 0, 0, 1, 2)
    control_body.addWidget(page.stop_btn, 1, 0)
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
        card, metric = page.metric_card(label)
        status_body.addWidget(card, 0, index)
        page.metric_labels[key] = metric
    actions.addWidget(status, 3)

    log_panel = Card()
    page.log = QTextEdit()
    page.prepare_readonly_text(page.log)
    log_panel.layout.addWidget(page.log, 1)
    layout.addWidget(log_panel, 1)


