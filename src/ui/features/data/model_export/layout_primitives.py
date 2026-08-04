from __future__ import annotations

from src.shared.qt import QCheckBox, QDoubleSpinBox, QSpinBox, QVBoxLayout, QWidget
from src.ui.features.data.model_export.controls import (
    configure_field_box as _configure_field_box,
    section_box as _section_box,
)


def _spin_field(page, label: str, value: int, minimum: int, maximum: int, help_text: str):
    box = QWidget()
    layout = QVBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    caption_box, _caption, _icon = page._caption_widget(label, help_text=help_text)
    spin = QSpinBox()
    spin.setRange(minimum, maximum)
    spin.setValue(int(value))
    layout.addWidget(caption_box)
    layout.addWidget(spin)
    return box, spin


def _double_spin_field(
    page,
    label: str,
    value: float,
    minimum: float,
    maximum: float,
    step: float,
    help_text: str,
):
    box = QWidget()
    layout = QVBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    caption_box, _caption, _icon = page._caption_widget(label, help_text=help_text)
    spin = QDoubleSpinBox()
    spin.setRange(minimum, maximum)
    spin.setSingleStep(step)
    spin.setDecimals(2)
    spin.setValue(float(value))
    layout.addWidget(caption_box)
    layout.addWidget(spin)
    return box, spin


def _checkbox(page, label: str, checked: bool, help_text: str) -> QCheckBox:
    checkbox = QCheckBox(label)
    checkbox.setChecked(bool(checked))
    page._set_help_target(checkbox, label, help_text)
    return checkbox
