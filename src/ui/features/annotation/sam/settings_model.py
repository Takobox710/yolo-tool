from __future__ import annotations

from math import exp, log


SAM_ASSIST_PARAMETER_DEFAULTS = {
    "multimask_output": False,
    "minimum_score": 0.0,
    "minimum_area": 4,
    "polygon_simplification_ratio": 0.002,
}

AREA_SLIDER_STEPS = 1000
MINIMUM_AREA = 1
MAXIMUM_AREA = 100_000_000


def area_from_slider(slider_value: int) -> int:
    fraction = max(0.0, min(1.0, float(slider_value) / AREA_SLIDER_STEPS))
    minimum_log = log(MINIMUM_AREA)
    maximum_log = log(MAXIMUM_AREA)
    return round(exp(minimum_log + (maximum_log - minimum_log) * fraction))


def slider_from_area(area: int) -> int:
    bounded = max(MINIMUM_AREA, min(MAXIMUM_AREA, int(area)))
    fraction = (log(bounded) - log(MINIMUM_AREA)) / (
        log(MAXIMUM_AREA) - log(MINIMUM_AREA)
    )
    return round(fraction * AREA_SLIDER_STEPS)


__all__ = [
    "AREA_SLIDER_STEPS",
    "MAXIMUM_AREA",
    "MINIMUM_AREA",
    "SAM_ASSIST_PARAMETER_DEFAULTS",
    "area_from_slider",
    "slider_from_area",
]
