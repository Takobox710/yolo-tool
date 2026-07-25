from __future__ import annotations

from src.ui.shared.page_base import BasePage
from src.shared.qt import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    Qt,
    QVBoxLayout,
)
from src.ui.features.data.convert.tab import ConvertTab
from src.ui.features.data.model_export.tab import ModelExportTab
from src.ui.features.data.preview.tab import PreviewTab
from src.ui.features.data.rename.tab import RenameTab
from src.ui.features.data.resize.tab import ResizeTab


class DataPage(BasePage):
    def __init__(self, app):
        super().__init__(app)
        layout = self.page_layout()
        layout.setContentsMargins(20, 14, 12, 12)
        layout.setSpacing(8)
        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(8)
        layout.addLayout(content, 1)
        sidebar = QFrame()
        sidebar.setObjectName("dataSidebar")
        sidebar.setFixedWidth(178)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(16, 22, 16, 18)
        side_layout.setSpacing(13)
        title = QLabel("数据处理")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("dataSidebarTitle")
        side_layout.addWidget(title)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("dataSidebarDivider")
        side_layout.addWidget(line)
        self.tool_stack = QStackedWidget()
        self.tools = {
            "convert": ConvertTab(app),
            "preview": PreviewTab(app),
            "rename": RenameTab(app),
            "resize": ResizeTab(app),
            "model_export": ModelExportTab(app),
        }
        self.tool_buttons = {}
        for key, label, icon in [
            ("convert", "🔄 数据集划分", None),
            ("preview", "🖼 标注预览", None),
            ("rename", "🏷 批量重命名", None),
            ("resize", "📦 图片压缩", None),
            ("model_export", "🗂️ 模型格式转换", None),
        ]:
            button = QPushButton(label)
            button.setObjectName("dataNavButton")
            if icon is not None:
                button.setIcon(self.style().standardIcon(icon))
            button.setCheckable(True)
            button.clicked.connect(
                lambda _checked=False, name=key: self.show_tool(name)
            )
            side_layout.addWidget(button)
            self.tool_buttons[key] = button
            self.tool_stack.addWidget(self.tools[key])
        side_layout.addStretch(1)
        content.addWidget(sidebar)
        content.addWidget(self.tool_stack, 1)
        self.show_tool("convert")

    def show_tool(self, key: str):
        self.tool_stack.setCurrentWidget(self.tools[key])
        for name, button in self.tool_buttons.items():
            button.setChecked(name == key)
