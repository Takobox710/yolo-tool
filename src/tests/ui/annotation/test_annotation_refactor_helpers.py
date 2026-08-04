from __future__ import annotations


def test_sam_settings_area_mapping_preserves_slider_boundaries():
    from src.ui.features.annotation.sam.settings_model import (
        area_from_slider,
        slider_from_area,
    )

    assert area_from_slider(0) == 1
    assert area_from_slider(1000) == 100_000_000
    assert slider_from_area(1) == 0
    assert slider_from_area(100_000_000) == 1000
