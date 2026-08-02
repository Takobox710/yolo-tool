from __future__ import annotations

from src.shared.qt import (
    QComboBox,
    QFrame,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


def section_box(title: str | None, object_name: str):
    box = QWidget()
    box.setObjectName(object_name)
    box.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
    outer = QVBoxLayout(box)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(5)
    if title:
        caption = QLabel(title)
        caption.setObjectName("modelExportSectionTitle")
        caption.setStyleSheet("color: #18344F; font-size: 14px; font-weight: 700;")
        outer.addWidget(caption)
        divider = QFrame()
        divider.setObjectName("modelExportSectionDivider")
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        divider.setFixedHeight(1)
        divider.setStyleSheet("background: #D9E3EC; color: #D9E3EC;")
        outer.addWidget(divider)
    content = QGridLayout()
    content.setContentsMargins(0, 0, 0, 0)
    outer.addLayout(content)
    return box, content


def configure_field_box(box: QWidget) -> None:
    box.setMinimumWidth(0)
    box.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
    for control in box.findChildren(QComboBox):
        control.setMinimumWidth(0)
        control.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
    for control in box.findChildren(QLineEdit):
        control.setMinimumWidth(0)
        control.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
    for button in box.findChildren(QPushButton):
        button.setFixedWidth(68)


def spin_control_field(label: str, spin):
    box = QWidget()
    layout = QVBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(3)
    caption = QLabel(label)
    caption.setObjectName("fieldLabel")
    layout.addWidget(caption)
    layout.addWidget(spin)
    return box


__all__ = ["configure_field_box", "section_box", "spin_control_field"]
