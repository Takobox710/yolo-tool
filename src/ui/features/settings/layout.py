from __future__ import annotations

from src.ui.features.settings.constants import STATUS_CARD_LABELS
from src.shared.qt import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


def build_settings_layout(page) -> None:
    layout = page.page_layout()
    title = QLabel("系统设置")
    title.setObjectName("pageTitle")
    layout.addWidget(title)

    info_outer = QFrame()
    info_outer.setObjectName("systemInfoOuter")
    info_outer_layout = QGridLayout(info_outer)
    info_outer_layout.setContentsMargins(0, 0, 0, 0)
    info_outer_layout.setSpacing(0)
    info_grid = QGridLayout()
    info_grid.setContentsMargins(12, 12, 12, 12)
    info_grid.setSpacing(8)
    page.status_cards = {}
    for index, label in enumerate(STATUS_CARD_LABELS):
        inner = QFrame()
        inner.setObjectName("systemInfoInner")
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(10, 8, 10, 8)
        lbl = QLabel(label)
        lbl.setObjectName("fieldLabel")
        value = QLabel("待检测")
        value.setObjectName("metricValue")
        value.setWordWrap(True)
        inner_layout.addWidget(lbl)
        inner_layout.addWidget(value)
        page.status_cards[label] = value
        info_grid.addWidget(inner, index // 4, index % 4)
    info_outer_layout.addLayout(info_grid, 0, 0)
    layout.addWidget(info_outer)

    controls_row = QFrame()
    controls_layout = QHBoxLayout(controls_row)
    controls_layout.setContentsMargins(0, 0, 0, 0)
    controls_layout.setSpacing(18)
    for widget in page._build_control_widgets():
        controls_layout.addWidget(widget)
    controls_layout.addStretch(1)
    page.reset_btn = QPushButton("恢复默认设置")
    page.reset_btn.setObjectName("softButton")
    page.reset_btn.clicked.connect(page._reset_defaults)
    controls_layout.addWidget(page.reset_btn)
    layout.addWidget(controls_row)

    log_panel = QFrame()
    log_panel.setObjectName("card")
    log_layout = QVBoxLayout(log_panel)
    log_layout.setContentsMargins(12, 10, 12, 12)
    log_layout.setSpacing(8)
    log_title = QLabel("程序日志")
    log_title.setObjectName("sectionTitle")
    log_layout.addWidget(log_title)

    page.log = QTextEdit()
    page.prepare_readonly_text(page.log)
    page.log.setPlainText(page.program_log_text())
    log_layout.addWidget(page.log, 1)
    layout.addWidget(log_panel, 1)
