from __future__ import annotations

from src.shared.qt import QHBoxLayout
from src.ui.features.validation.left_layout import build_validation_left_layout
from src.ui.features.validation.result_layout import build_validation_result_layout


def build_validation_layout(page, context) -> None:
    layout = page.page_layout()
    layout.setContentsMargins(16, 16, 16, 16)
    page.validation_layout = layout
    split = QHBoxLayout()
    page.validation_split_layout = split
    layout.addLayout(split, 1)
    build_validation_left_layout(page, context, split)
    build_validation_result_layout(page, split)


__all__ = ["build_validation_layout"]
