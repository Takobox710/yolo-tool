from __future__ import annotations

from src.services.model_export import export_display_names, resolve_export_format
from src.shared.qt import QGridLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton, QTextEdit, QVBoxLayout


def build_model_export_layout(page) -> None:
    settings = page.context.settings.model_export
    layout = QVBoxLayout(page)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(12)
    grid = QGridLayout()
    grid.setHorizontalSpacing(12)
    grid.setVerticalSpacing(10)
    page.model_box, page.model_combo = page.stacked_combo_field(
        "源模型", page._model_display_path(settings.model_path), [], page.choose_model,
        "选择 .pt 模型", "仅支持从 Ultralytics YOLO .pt 模型导出。",
    )
    page.output_box, page.output_edit = page.path_field(
        "输出目录", settings.output_dir, page.choose_dir, "选择模型转换结果目录"
    )
    page.format_box, page.format_combo = page.combo_field(
        "目标格式", resolve_export_format(settings.format).display_name, export_display_names()
    )
    page.imgsz_box, page.imgsz_edit = page.field(
        "输入尺寸", str(settings.imgsz), placeholder="例如 640",
        help_text="YOLO 导出使用该尺寸；SAM2 ONNX 固定使用 1024，输出编码器和点提示解码器两个文件。",
    )
    page.simplify_box, page.simplify_check = page.checkbox_with_help(
        "简化 ONNX", settings.simplify, "仅用于 ONNX 和 TensorRT 的中间 ONNX 图。"
    )
    grid.addWidget(page.model_box, 0, 0)
    grid.addWidget(page.output_box, 0, 1)
    grid.addWidget(page.format_box, 1, 0)
    grid.addWidget(page.imgsz_box, 1, 1)
    grid.addWidget(page.simplify_box, 2, 0)
    page.install_btn = QPushButton("安装/替换附加包")
    page.install_btn.setFixedWidth(150)
    page.install_btn.setToolTip("选择并安装或替换模型格式转换附加环境包")
    page.install_btn.clicked.connect(page.choose_model_export_package)
    page.install_progress = QProgressBar()
    page.install_progress.setRange(0, 100)
    page.install_progress.setValue(0)
    page.install_progress.setFormat("正在安装 %p%")
    page.install_progress.setMinimumWidth(180)
    page.install_progress.setVisible(False)
    page.install_controls = QHBoxLayout()
    page.install_controls.setContentsMargins(0, 0, 0, 0)
    page.install_controls.setSpacing(8)
    page.install_controls.addStretch(1)
    page.install_controls.addWidget(page.install_btn)
    page.install_controls.addWidget(page.install_progress, 1)
    grid.addLayout(page.install_controls, 2, 1)
    page.environment_status = QLabel()
    page.environment_status.setVisible(False)
    layout.addLayout(grid)
    actions = QHBoxLayout()
    page.preview_btn = QPushButton("预览转换")
    page.preview_btn.clicked.connect(page.preview_export)
    page.start_btn = QPushButton("开始转换")
    page.start_btn.clicked.connect(page.start_export)
    page.stop_btn = QPushButton("停止")
    page.stop_btn.setEnabled(False)
    page.stop_btn.clicked.connect(page.stop_export)
    page.open_btn = QPushButton("打开结果文件夹")
    page.open_btn.clicked.connect(page.open_output_dir)
    for button in (page.preview_btn, page.start_btn, page.stop_btn, page.open_btn):
        actions.addWidget(button)
    actions.addStretch(1)
    layout.addLayout(actions)
    page.log = QTextEdit()
    page.prepare_readonly_text(page.log)
    page.log.setAcceptDrops(False)
    page.model_combo.setAcceptDrops(False)
    page.output_edit.setAcceptDrops(False)
    page.imgsz_edit.setAcceptDrops(False)
    page.log.setPlaceholderText("预览或转换后将在这里显示环境、目标路径和运行日志。")
    layout.addWidget(page.log, 1)


__all__ = ["build_model_export_layout"]
