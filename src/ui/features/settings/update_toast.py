from __future__ import annotations

from src.services.runtime.release_updates import ReleaseCheckResult
from src.shared.qt import (
    QColor,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPropertyAnimation,
    QPoint,
    QRect,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    Qt,
    QTimer,
)


class ReleaseCheckToast(QFrame):
    """A non-modal status toast anchored to the settings page."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("releaseCheckToast")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedSize(420, 84)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 18)
        shadow.setColor(QColor(0, 0, 0, 77))
        self.setGraphicsEffect(shadow)

        self.progress = QFrame(self)
        self.progress.setObjectName("releaseCheckProgress")
        self.progress.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 16, 14, 14)
        layout.setSpacing(12)

        icon_box = QFrame()
        icon_box.setObjectName("releaseCheckIconBox")
        icon_box.setFixedSize(38, 38)
        icon_layout = QHBoxLayout(icon_box)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        self.icon = QLabel("✓")
        self.icon.setObjectName("releaseCheckIcon")
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_layout.addWidget(self.icon)
        layout.addWidget(icon_box, 0, Qt.AlignmentFlag.AlignVCenter)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(0)
        self.title = QLabel("GitHub Release 检查")
        self.title.setObjectName("releaseCheckTitle")
        text_layout.addWidget(self.title)
        self.message = QLabel()
        self.message.setObjectName("releaseCheckMessage")
        self.message.setWordWrap(True)
        self.message.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        text_layout.addWidget(self.message)

        layout.addLayout(text_layout, 1)

        close_button = QToolButton()
        close_button.setObjectName("releaseCheckClose")
        close_button.setAutoRaise(True)
        close_button.setFixedSize(22, 22)
        close_button.setText("×")
        close_button.setToolTip("关闭")
        close_button.clicked.connect(self.hide)
        layout.addWidget(close_button, 0, Qt.AlignmentFlag.AlignTop)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)
        self._progress_animation = QPropertyAnimation(self.progress, b"geometry", self)
        self._progress_animation.setDuration(4200)
        self._entrance_animation = QPropertyAnimation(self, b"pos", self)
        self._entrance_animation.setDuration(180)


    def show_result(self, result: ReleaseCheckResult) -> None:
        if result.error:
            message = "暂时无法获取最新版本。"
            icon_text = "!"
        elif result.update_available:
            message = f"发现新版本 {result.latest_version}。"
            icon_text = "✓"
        else:
            message = "当前已是最新版本。"
            icon_text = "✓"
        self.message.setText(message)
        self.icon.setText(icon_text)
        self.setProperty("failed", bool(result.error))
        self.style().unpolish(self)
        self.style().polish(self)
        self._hide_timer.start(4200)
        self.adjust_position()
        self._progress_animation.stop()
        self._progress_animation.setStartValue(QRect(0, 0, self.width(), 3))
        self._progress_animation.setEndValue(QRect(0, 0, 0, 3))
        target = self.pos()
        self._entrance_animation.stop()
        self._entrance_animation.setStartValue(QPoint(target.x(), target.y() - 10))
        self._entrance_animation.setEndValue(target)
        self.move(target.x(), target.y() - 10)
        self.show()
        self.raise_()
        self.progress.raise_()
        self._entrance_animation.start()
        self._progress_animation.start()

    def adjust_position(self) -> None:
        parent = self.parentWidget()
        if parent is not None:
            self.move(max(16, (parent.width() - self.width()) // 2), 16)
        self.progress.setGeometry(0, 0, self.width(), 3)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjust_position()
