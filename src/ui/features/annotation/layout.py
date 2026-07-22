from __future__ import annotations

from src.shared.qt import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
)
from src.ui.features.annotation.canvas.widget import AnnotationCanvas


def build_center(page) -> QVBoxLayout:
    layout = QVBoxLayout()
    layout.setContentsMargins(0, 2, 0, 0)
    layout.setSpacing(0)
    page.canvas = AnnotationCanvas()
    page.canvas.changed_callback = page.mark_dirty_and_save
    page.canvas.selection_callback = page.sync_selection
    layout.addWidget(page.canvas, 1)
    return layout


def build_status_bar(page) -> QStatusBar:
    status_bar = QStatusBar(page)
    status_bar.setObjectName("annotationStatusBar")
    status_bar.setSizeGripEnabled(False)
    status_bar.setVisible(False)
    page.annotation_status_bar = status_bar
    return status_bar


def set_annotation_bottom_margin(page, bottom: int) -> None:
    margins = page.annotation_root_layout.contentsMargins()
    if margins.bottom() == bottom:
        return
    page.annotation_root_layout.setContentsMargins(
        margins.left(), margins.top(), margins.right(), bottom
    )


def build_right_panel(page) -> QFrame:
    panel = QFrame()
    panel.setObjectName("annotationRightPanel")
    panel.setFixedWidth(230)
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    mode_label = QLabel("任务类别：")
    mode_label.setObjectName("annotationPathLabel")
    layout.addWidget(mode_label)
    page.output_mode_combo = QComboBox()
    page.output_mode_combo.addItems(["detect", "obb"])
    page.output_mode_combo.setCurrentText(
        page.output_mode if page.output_mode in {"detect", "obb"} else "detect"
    )
    page.output_mode_combo.currentTextChanged.connect(page.change_output_mode)
    layout.addWidget(page.output_mode_combo)
    class_label = QLabel("标注类别：")
    class_label.setObjectName("annotationPathLabel")
    layout.addWidget(class_label)
    page.class_combo = QComboBox()
    page.class_combo.currentIndexChanged.connect(page.change_class)
    layout.addWidget(page.class_combo)
    manage_btn = QPushButton("🏷 管理类别")
    manage_btn.setObjectName("annotationPrimaryButton")
    manage_btn.clicked.connect(page.manage_classes)
    layout.addWidget(manage_btn)
    page.annotation_list = QListWidget()
    page.annotation_list.currentRowChanged.connect(page.select_annotation)
    page.annotation_list.setContextMenuPolicy(page._custom_context_menu_policy())
    page.annotation_list.customContextMenuRequested.connect(page.open_annotation_list_context_menu)
    layout.addWidget(page.annotation_list, 2)
    delete_btn = QPushButton("🗑 删除选中框(Del)")
    delete_btn.setObjectName("annotationPrimaryButton")
    delete_btn.clicked.connect(page.delete_selected)
    layout.addWidget(delete_btn)
    file_header = QHBoxLayout()
    file_header.setContentsMargins(0, 0, 0, 0)
    file_header.setSpacing(6)
    file_label = QLabel("图片列表：")
    file_label.setObjectName("annotationPathLabel")
    file_header.addWidget(file_label)
    file_header.addStretch(1)
    page.file_count_label = QLabel("0/0")
    page.file_count_label.setObjectName("annotationPathLabel")
    file_header.addWidget(page.file_count_label)
    layout.addLayout(file_header)
    page.file_list = QListWidget()
    page.file_list.setUniformItemSizes(True)
    page.file_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    page.file_list.viewport().installEventFilter(page)
    page.file_list.currentRowChanged.connect(page.jump_to_file)
    page.file_list.setContextMenuPolicy(page._custom_context_menu_policy())
    page.file_list.customContextMenuRequested.connect(page.open_file_list_context_menu)
    layout.addWidget(page.file_list, 3)
    return panel
