from __future__ import annotations

from scr.ui.page_base import BasePage
from scr.ui.qt import QFrame, QHBoxLayout, QLabel, QPushButton, QStackedWidget, QVBoxLayout
from scr.ui.views.convert import ConvertTab
from scr.ui.views.preview import PreviewTab
from scr.ui.views.rename import RenameTab
from scr.ui.views.resize import ResizeTab

class DataPage(BasePage):
    def __init__(self, app):
        super().__init__(app)
        layout = self.page_layout()
        content = QHBoxLayout()
        layout.addLayout(content, 1)
        sidebar = QFrame()
        sidebar.setObjectName("dataSidebar")
        sidebar.setFixedWidth(180)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(12, 18, 12, 18)
        title = QLabel("数据处理")
        title.setObjectName("sideTitle")
        side_layout.addWidget(title)
        self.tool_stack = QStackedWidget()
        self.tools = {
            "convert": ConvertTab(app),
            "preview": PreviewTab(app),
            "rename": RenameTab(app),
            "resize": ResizeTab(app),
        }
        self.tool_buttons = {}
        for key, label in [
            ("convert", "标注转换"),
            ("preview", "标注预览"),
            ("rename", "批量重命名"),
            ("resize", "图片压缩"),
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
