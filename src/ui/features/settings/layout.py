from __future__ import annotations

from src.ui.features.settings.constants import STATUS_CARD_LABELS
from src.shared.qt import (
    QColor,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QIcon,
    QPainter,
    QPen,
    QPixmap,
    QPushButton,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QSize,
    Signal,
    Qt,
)


class _ClickableLabel(QLabel):
    clicked = Signal()

    def mousePressEvent(self, event):  # noqa: N802 - Qt API name
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


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
    for column in range(4):
        info_grid.setColumnStretch(column, 1)
    page.status_cards = {}
    for index, label in enumerate(STATUS_CARD_LABELS):
        inner = QFrame()
        inner.setObjectName("systemInfoInner")
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(10, 8, 10, 8)
        lbl = QLabel(label)
        lbl.setObjectName("fieldLabel")
        value = _ClickableLabel("待检测") if label == "程序版本" else QLabel("待检测")
        value.setObjectName("metricValue")
        value.setWordWrap(True)
        inner_layout.addWidget(lbl)
        if label == "程序版本":
            value.setCursor(Qt.CursorShape.PointingHandCursor)
            value.setToolTip("查看版本更新")
            value.clicked.connect(page.open_release_update_dialog)
            version_row = QHBoxLayout()
            version_row.setContentsMargins(0, 0, 0, 0)
            version_row.setSpacing(4)
            version_row.addWidget(value)
            page.upgrade_indicator = QToolButton()
            page.upgrade_indicator.setObjectName("upgradeIndicator")
            page.upgrade_indicator.setAutoRaise(True)
            page.upgrade_indicator.setFixedSize(26, 26)
            page.upgrade_indicator.setIcon(_build_update_icon())
            page.upgrade_indicator.setIconSize(QSize(18, 18))
            page.upgrade_indicator.setCursor(Qt.CursorShape.PointingHandCursor)
            page.upgrade_indicator.setToolTip("查看版本更新")
            page.upgrade_indicator.hide()
            page.upgrade_indicator.clicked.connect(page.open_release_update_dialog)
            version_row.addWidget(
                page.upgrade_indicator,
                0,
                Qt.AlignmentFlag.AlignBottom,
            )
            version_row.addStretch(1)
            inner_layout.addLayout(version_row)
        else:
            inner_layout.addWidget(value)
        page.status_cards[label] = value
        info_grid.addWidget(inner, index // 4, index % 4)
    page.release_check_result = None
    info_outer_layout.addLayout(info_grid, 0, 0)
    layout.addWidget(info_outer)

    from src.ui.features.settings.update_toast import ReleaseCheckToast

    page.release_check_toast = ReleaseCheckToast(page)
    page.release_check_toast.hide()

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
    page.log.setAcceptDrops(False)
    page.log.setPlainText(page.program_log_text())
    log_layout.addWidget(page.log, 1)
    layout.addWidget(log_panel, 1)


def _build_update_icon():
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor("#208FD4"), 2.2))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawEllipse(3.5, 3.5, 25, 25)
    painter.drawLine(16, 22, 16, 10)
    painter.drawLine(11, 15, 16, 10)
    painter.drawLine(21, 15, 16, 10)
    painter.end()
    return QIcon(pixmap)
