"""Compatibility façade for model-export layout components."""

from src.services.runtime.variant import CPU_VARIANT, installed_variant
from src.ui.features.data.model_export.layout_actions import build_action_row
from src.ui.features.data.model_export import layout_base as _base
from src.ui.features.data.model_export.layout_responsive import (
    arrange_basic_option_row,
    update_model_export_card_ratio,
)

__all__ = ["arrange_basic_option_row", "build_model_export_layout", "update_model_export_card_ratio"]


def build_model_export_layout(page) -> None:
    _base.installed_variant = installed_variant
    _base.CPU_VARIANT = CPU_VARIANT
    _base.build_model_export_layout(page)
