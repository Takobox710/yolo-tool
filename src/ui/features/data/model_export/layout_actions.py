from __future__ import annotations

from src.services.runtime.variant import CPU_VARIANT, installed_variant
from src.shared.qt import QHBoxLayout, QLabel, QPushButton, QSizePolicy


def build_action_row(page, root_layout) -> None:
    page.install_btn = QPushButton("安装/替换附加包")
    page.install_btn.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
    page.install_btn.setFixedWidth(144)
    page.install_btn.setToolTip("选择并安装或替换模型格式转换附加环境包")
    page.install_btn.clicked.connect(page.choose_model_export_package)
    page.install_status = QLabel()
    page.install_status.setMinimumWidth(150)
    page.install_status.setVisible(False)
    page.install_controls = QHBoxLayout()
    page.install_controls.setContentsMargins(0, 0, 0, 0)
    page.install_controls.setSpacing(8)
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
        button.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        page.install_controls.addWidget(button)
    page.install_controls.addStretch(1)
    page.install_controls.addWidget(page.install_btn)
    page.install_controls.addWidget(page.install_status)
    root_layout.addLayout(page.install_controls)
    page.install_btn.setVisible(installed_variant() != CPU_VARIANT)


__all__ = ["build_action_row"]
