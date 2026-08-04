"""Compatibility exports for the model-export layout builder.

The concrete widget construction lives in ``layout_components`` so the page
module can keep a stable import path while layout responsibilities continue to
be split into smaller modules.
"""

from src.ui.features.data.model_export import layout_actions as _actions
from src.ui.features.data.model_export import layout_base as _base
from src.ui.features.data.model_export import layout_components as _components
from src.services.runtime.variant import CPU_VARIANT, installed_variant


arrange_basic_option_row = _components.arrange_basic_option_row
update_model_export_card_ratio = _components.update_model_export_card_ratio


def build_model_export_layout(page) -> None:
    # Preserve the old monkeypatch seam used by UI tests and compatibility code.
    _components.installed_variant = installed_variant
    _components.CPU_VARIANT = CPU_VARIANT
    _base.installed_variant = installed_variant
    _base.CPU_VARIANT = CPU_VARIANT
    _actions.installed_variant = installed_variant
    _actions.CPU_VARIANT = CPU_VARIANT
    _components.build_model_export_layout(page)

__all__ = [
    "arrange_basic_option_row",
    "build_model_export_layout",
    "update_model_export_card_ratio",
    "CPU_VARIANT",
    "installed_variant",
]
