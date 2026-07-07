from __future__ import annotations

from scr.ui.page_base import BasePage
from scr.ui.qt import QFrame, QHBoxLayout, QLabel, QPushButton, QStackedWidget, Qt, QVBoxLayout
from scr.ui.views.convert import ConvertTab
from scr.ui.views.preview import PreviewTab
from scr.ui.views.rename import RenameTab
from scr.ui.views.resize import ResizeTab


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
        }
        self.tool_buttons = {}
        for key, label in [
            ("convert", "🔄 标注转换"),
            ("preview", "🖼 标注预览"),
            ("rename", "🏷 批量重命名"),
            ("resize", "📦 图片压缩"),
        ]:
            button = QPushButton(label)
            button.setObjectName("dataNavButton")
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
