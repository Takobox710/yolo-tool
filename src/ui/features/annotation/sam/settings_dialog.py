from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtGui import QDesktopServices

from src.shared.qt import QDialog, QUrl, QVBoxLayout
from src.ui.features.annotation.sam.settings_layout import (
    apply_style,
    build_footer,
    build_model_section,
    build_quality_section,
    build_result_section,
)
from src.ui.features.annotation.sam.settings_model import (
    AREA_SLIDER_STEPS,
    MAXIMUM_AREA,
    MINIMUM_AREA,
    SAM_ASSIST_PARAMETER_DEFAULTS,
    area_from_slider,
    slider_from_area,
)


class SamAdvancedSettingsDialog(QDialog):
    _AREA_SLIDER_STEPS = AREA_SLIDER_STEPS
    _MINIMUM_AREA = MINIMUM_AREA
    _MAXIMUM_AREA = MAXIMUM_AREA

    def __init__(
        self,
        values: dict[str, Any] | None = None,
        model_name: str = "",
        parent=None,
        *,
        sam_models=None,
        selected_model_key: str = "",
    ) -> None:
        super().__init__(parent)
        self.sam_models = list(sam_models or [])
        self.model_name = model_name
        self.selected_model_key_value = selected_model_key
        self.area_slider_steps = self._AREA_SLIDER_STEPS
        self.minimum_area = self._MINIMUM_AREA
        self.maximum_area = self._MAXIMUM_AREA
        self.setObjectName("samAdvancedDialog")
        self.setWindowTitle("SAM 高级设置")
        self.resize(480, 400)
        self.setMinimumSize(440, 360)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 18)
        root.setSpacing(14)
        build_model_section(self, root)
        build_quality_section(self, root)
        build_result_section(self, root)
        build_footer(self, root)

        self.score_slider.valueChanged.connect(
            lambda value: self.score_spin.setValue(value * 0.05)
        )
        self.score_spin.valueChanged.connect(
            lambda value: self.score_slider.setValue(round(float(value) / 0.05))
        )
        self.area_slider.valueChanged.connect(self._update_area_spin)
        self.area_spin.valueChanged.connect(self._update_area_slider)
        self.simplify_slider.valueChanged.connect(
            lambda value: self.simplify_spin.setValue(value * 0.05)
        )
        self.simplify_spin.valueChanged.connect(
            lambda value: self.simplify_slider.setValue(round(float(value) / 0.05))
        )
        self.set_values(values or SAM_ASSIST_PARAMETER_DEFAULTS)
        apply_style(self)

    def values(self) -> dict[str, Any]:
        return {
            "multimask_output": self.best_candidate_button.isChecked(),
            "minimum_score": float(self.score_spin.value()),
            "minimum_area": int(self.area_spin.value()),
            "polygon_simplification_ratio": float(self.simplify_spin.value()) / 100.0,
        }

    def _update_area_spin(self, slider_value: int) -> None:
        self.area_spin.setValue(self._area_from_slider(slider_value))

    def _update_area_slider(self, area: int) -> None:
        self.area_slider.setValue(self._slider_from_area(area))

    @classmethod
    def _area_from_slider(cls, slider_value: int) -> int:
        return area_from_slider(slider_value)

    @classmethod
    def _slider_from_area(cls, area: int) -> int:
        return slider_from_area(area)

    def selected_model_key(self) -> str:
        return str(self.model_combo.currentData() or "")

    def _open_model_folder(self) -> None:
        selected_key = self.selected_model_key()
        selected_model = next(
            (model for model in self.sam_models if model.key == selected_key),
            None,
        )
        if selected_model is None:
            return
        target = Path(selected_model.checkpoint_path)
        folder = target if target.is_dir() else target.parent
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder.resolve())))

    def set_values(self, values: dict[str, Any]) -> None:
        multimask = bool(values.get("multimask_output", False))
        self.best_candidate_button.setChecked(multimask)
        self.fast_candidate_button.setChecked(not multimask)
        self.score_spin.setValue(
            max(0.0, min(1.0, float(values.get("minimum_score", 0.0))))
        )
        self.area_spin.setValue(
            max(
                self._MINIMUM_AREA,
                min(self._MAXIMUM_AREA, int(values.get("minimum_area", 4))),
            )
        )
        ratio = max(
            0.0,
            min(0.015, float(values.get("polygon_simplification_ratio", 0.002))),
        )
        self.simplify_spin.setValue(ratio * 100.0)

    def reset_defaults(self) -> None:
        self.set_values(SAM_ASSIST_PARAMETER_DEFAULTS)


__all__ = ["SAM_ASSIST_PARAMETER_DEFAULTS", "SamAdvancedSettingsDialog"]
