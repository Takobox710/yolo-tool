from __future__ import annotations

from PySide6.QtCore import Property, QEasingCurve, QRectF, QSize
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton

from src.shared.qt import QPropertyAnimation, Qt


class AnimatedToggleSwitch(QAbstractButton):
    def __init__(self, parent=None, *, width: int = 44, height: int = 24) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._switch_width = max(24, int(width))
        self._switch_height = max(16, int(height))
        self.setFixedSize(self._switch_width, self._switch_height)
        self._thumb_position = 0.0
        self._animation = QPropertyAnimation(self, b"thumbPosition", self)
        self._animation.setDuration(140)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggled.connect(self._animate_to_state)

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt API name
        return QSize(self._switch_width, self._switch_height)

    def setChecked(self, checked: bool) -> None:  # noqa: N802 - Qt API name
        super().setChecked(bool(checked))
        if self.signalsBlocked() or self._animation.state() != QPropertyAnimation.State.Running:
            self._animation.stop()
            self._thumb_position = 1.0 if checked else 0.0
            self.update()

    def _animate_to_state(self, checked: bool) -> None:
        self._animation.stop()
        self._animation.setStartValue(self._thumb_position)
        self._animation.setEndValue(1.0 if checked else 0.0)
        self._animation.start()

    def _get_thumb_position(self) -> float:
        return self._thumb_position

    def _set_thumb_position(self, position: float) -> None:
        self._thumb_position = max(0.0, min(1.0, float(position)))
        self.update()

    thumbPosition = Property(float, _get_thumb_position, _set_thumb_position)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API name
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        track = QColor("#22C55E") if self.isChecked() else QColor("#8493A3")
        if not self.isEnabled():
            track.setAlpha(110)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track)
        radius = self.height() / 2.0
        painter.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), radius, radius)
        diameter = float(max(12, min(20, self.height() - 4)))
        left = 2.0 + self._thumb_position * (self.width() - diameter - 4.0)
        painter.setBrush(QColor("#FFFFFF"))
        top = (self.height() - diameter) / 2.0
        painter.drawEllipse(QRectF(left, top, diameter, diameter))
        if self.hasFocus():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor("#208FD4"), 1))
            focus_radius = max(1.0, (self.height() - 1) / 2.0)
            painter.drawRoundedRect(
                QRectF(0.5, 0.5, self.width() - 1, self.height() - 1),
                focus_radius,
                focus_radius,
            )


__all__ = ["AnimatedToggleSwitch"]
