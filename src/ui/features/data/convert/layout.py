from __future__ import annotations

from src.shared.qt import QGridLayout, QHBoxLayout, QPushButton, QTextEdit, QVBoxLayout
from src.ui.shared.page_base import Card


LABELME_MODE = "Labelme 转 YOLO 并划分数据集"
YOLO_MODE = "YOLO 原生数据集划分"


def build_convert_layout(page) -> None:
    context = page.context
    layout = QVBoxLayout(page)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(12)
    paths = context.settings.paths
    dataset = context.settings.dataset

    top_row = QHBoxLayout()
    top_row.setContentsMargins(0, 0, 0, 0)
    top_row.setSpacing(16)
    left_card = Card("数据集划分配置")
    left_grid = QGridLayout()
    left_grid.setHorizontalSpacing(12)
    left_grid.setVerticalSpacing(10)
    page.images_box, page.images_edit = page.path_field("图片目录", paths.images_dir, page.choose_dir, "选择待转换的图片目录")
    page.annotations_box, page.annotations_edit = page.path_field("Labelme 标注目录", paths.annotations_dir, page.choose_dir, "选择 Labelme 标注目录")
    page.yolo_labels_box, page.yolo_labels_edit = page.path_field("YOLO 标注目录", paths.labels_dir, page.choose_dir, "选择已有 YOLO 标注目录")
    page.output_box, page.output_edit = page.path_field("数据集输出目录", paths.dataset_dir, page.choose_dir, "选择数据集输出目录")
    left_grid.addWidget(page.images_box, 0, 0)
    left_grid.addWidget(page.annotations_box, 0, 1)
    left_grid.addWidget(page.yolo_labels_box, 1, 0)
    left_grid.addWidget(page.output_box, 1, 1)
    left_card.layout.addLayout(left_grid)

    controls_row = QHBoxLayout()
    controls_row.setContentsMargins(0, 0, 0, 0)
    controls_row.setSpacing(12)
    backup_box, page.backup_yolo_check = page.checkbox_with_help(
        "备份标注文件",
        context.settings.conversion.backup_yolo_files,
        help_text="开启后会把本次转换生成的 YOLO 标注文件和 data.yaml 备份到 data/old 下独立文件夹中，支持多次备份共存。",
    )
    controls_row.addWidget(backup_box)
    controls_row.addStretch(1)
    page.class_mapping_btn = QPushButton("自定义类别名称")
    page.class_mapping_btn.setObjectName("softButton")
    page.class_mapping_btn.setFixedWidth(130)
    page.class_mapping_btn.clicked.connect(page.open_class_mapping_dialog)
    controls_row.addWidget(page.class_mapping_btn)
    left_card.layout.addLayout(controls_row)

    right_card = Card("转换参数")
    param_grid = QGridLayout()
    param_grid.setHorizontalSpacing(12)
    param_grid.setVerticalSpacing(10)
    mode = LABELME_MODE if context.settings.conversion.use_labelme else YOLO_MODE
    page.mode_box, page.mode_combo = page.hint_combo_field("模式选择", mode, [LABELME_MODE, YOLO_MODE], "选择 Labelme 转换后划分数据集，或直接对已有 YOLO 标注进行数据集划分。")
    page.task_box, page.task_combo = page.hint_combo_field("任务类型", context.settings.task.mode, ["detect", "obb", "seg"], "OBB 输出旋转框标签；seg 输出多边形标签；detect 输出普通矩形框标签。")
    ratios = dataset.split_ratios
    page.train_ratio_box, page.train_ratio_edit = page.hint_field("训练", str(ratios.train), "训练集比例，三项合计必须为 1.0。", placeholder="0.0 - 1.0")
    page.val_ratio_box, page.val_ratio_edit = page.hint_field("验证", str(ratios.val), "验证集比例，用于训练中评估模型。", placeholder="0.0 - 1.0")
    page.test_ratio_box, page.test_ratio_edit = page.hint_field("测试", str(ratios.test), "测试集比例，用于最终检测泛化效果。", placeholder="0.0 - 1.0")
    param_grid.addWidget(page.mode_box, 0, 0, 1, 2)
    param_grid.addWidget(page.task_box, 1, 0)
    param_grid.addWidget(page.train_ratio_box, 1, 1)
    param_grid.addWidget(page.val_ratio_box, 2, 0)
    param_grid.addWidget(page.test_ratio_box, 2, 1)
    right_card.layout.addLayout(param_grid)
    top_row.addWidget(left_card, 3)
    top_row.addWidget(right_card, 2)
    layout.addLayout(top_row)

    actions = QHBoxLayout()
    preview_button = QPushButton("预览划分")
    preview_button.clicked.connect(page.preview)
    run_button = QPushButton("执行划分")
    run_button.clicked.connect(page.run)
    actions.addWidget(preview_button)
    actions.addWidget(run_button)
    actions.addStretch(1)
    layout.addLayout(actions)
    page.log = QTextEdit()
    page.prepare_readonly_text(page.log)
    page.log.setPlaceholderText("预览或执行后将在这里显示数据集划分、类别统计、跳过标签与输出路径。")
    layout.addWidget(page.log, 1)


__all__ = ["LABELME_MODE", "YOLO_MODE", "build_convert_layout"]
