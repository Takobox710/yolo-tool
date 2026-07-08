from __future__ import annotations

from src.shared.qt import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStyle,
    QVBoxLayout,
    Qt,
)


def build_toolbar(page) -> QFrame:
    sidebar = QFrame()
    sidebar.setObjectName("annotationSidebar")
    sidebar.setFixedWidth(178)
    layout = QVBoxLayout(sidebar)
    layout.setContentsMargins(16, 22, 16, 18)
    layout.setSpacing(13)
    title = QLabel("数据标注")
    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    title.setObjectName("annotationTitle")
    page._set_help_target(
        title,
        "数据标注",
        "可通过右键菜单快速切换标注类型，默认保存和读取 Labelme 格式标注；可通过“更多设置”开启 YOLO 格式文件保存。",
    )
    layout.addWidget(title)
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setObjectName("annotationDivider")
    layout.addWidget(line)
    image_icon = page.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)
    for text, slot, icon in [
        ("图片文件夹", page.choose_image_dir, image_icon),
        ("标签文件夹", page.choose_label_dir, image_icon),
        ("⬅️上一张(A)", page.prev_image, None),
        ("➡️下一张(D)", page.next_image, None),
        ("✎ 画标注框(W)", page.enable_draw_mode, None),
    ]:
        button = QPushButton(text)
        button.setObjectName("annotationToolButton")
        if text in {"⬅️上一张(A)", "➡️下一张(D)"}:
            button.setProperty("compactArrowButton", True)
            button.style().unpolish(button)
            button.style().polish(button)
        if icon is not None:
            button.setIcon(icon)
        button.clicked.connect(slot)
        layout.addWidget(button)
    ai_btn = QPushButton("🤖 AI预标注")
    ai_btn.setObjectName("annotationToolButton")
    ai_btn.clicked.connect(page.open_ai_prelabel_dialog)
    layout.addWidget(ai_btn)
    settings_btn = QPushButton("⚙ 更多设置")
    settings_btn.setObjectName("annotationToolButton")
    settings_btn.clicked.connect(page.open_annotation_settings)
    layout.addWidget(settings_btn)
    layout.addStretch(1)
    return sidebar
