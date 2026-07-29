from __future__ import annotations

from math import exp, log
from typing import Any

from PySide6.QtGui import QDesktopServices

from src.shared.qt import (
    QButtonGroup,
    QAbstractSpinBox,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QSizePolicy,
    QUrl,
    QSlider,
    QSpinBox,
    Qt,
    QVBoxLayout,
)


SAM_ASSIST_PARAMETER_DEFAULTS = {
    "multimask_output": False,
    "minimum_score": 0.0,
    "minimum_area": 4,
    "polygon_simplification_ratio": 0.002,
}


class SamAdvancedSettingsDialog(QDialog):
    _AREA_SLIDER_STEPS = 1000
    _MINIMUM_AREA = 1
    _MAXIMUM_AREA = 100_000_000

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
        self.setObjectName("samAdvancedDialog")
        self.setWindowTitle("SAM 高级设置")
        self.resize(480, 400)
        self.setMinimumSize(440, 360)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 18)
        root.setSpacing(14)

        model_row = QHBoxLayout()
        model_row.setContentsMargins(0, 0, 0, 0)
        model_caption = QLabel("当前模型")
        model_caption.setObjectName("samAdvancedCaption")
        model_row.addWidget(model_caption)
        self.model_combo = QComboBox()
        self.model_combo.setObjectName("samAdvancedModelCombo")
        self.model_combo.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Fixed,
        )
        for model in self.sam_models:
            self.model_combo.addItem(model.display_name, model.key)
        selected_index = self.model_combo.findData(selected_model_key)
        if selected_index < 0 and model_name:
            selected_index = self.model_combo.findText(model_name)
        if selected_index >= 0:
            self.model_combo.setCurrentIndex(selected_index)
        elif not self.sam_models:
            self.model_combo.addItem(str(model_name or "未选择"))
        self.model_combo.setEnabled(bool(self.sam_models))
        model_row.addWidget(self.model_combo, 1)
        self.open_model_folder_button = QPushButton("打开文件夹")
        self.open_model_folder_button.setObjectName("samOpenModelFolder")
        self.open_model_folder_button.setToolTip("打开当前模型所在文件夹")
        self.open_model_folder_button.setFixedWidth(104)
        self.open_model_folder_button.clicked.connect(self._open_model_folder)
        self.open_model_folder_button.setEnabled(bool(self.sam_models))
        model_row.addWidget(self.open_model_folder_button)
        root.addLayout(model_row)
        root.addWidget(self._separator())

        quality_title = QLabel("预测质量")
        quality_title.setObjectName("samAdvancedSectionTitle")
        root.addWidget(quality_title)
        quality_grid = QGridLayout()
        quality_grid.setContentsMargins(0, 0, 0, 0)
        quality_grid.setHorizontalSpacing(12)
        quality_grid.setVerticalSpacing(12)

        candidate_label = QLabel("候选掩码")
        candidate_label.setToolTip("单结果速度更快；三候选会选择预测质量最高的掩码。")
        quality_grid.addWidget(candidate_label, 0, 0)
        candidate_row = QHBoxLayout()
        candidate_row.setContentsMargins(0, 0, 0, 0)
        candidate_row.setSpacing(0)
        self.candidate_group = QButtonGroup(self)
        self.candidate_group.setExclusive(True)
        self.fast_candidate_button = QPushButton("快速单结果")
        self.fast_candidate_button.setObjectName("samSegmentLeft")
        self.fast_candidate_button.setCheckable(True)
        self.best_candidate_button = QPushButton("三候选优选")
        self.best_candidate_button.setObjectName("samSegmentRight")
        self.best_candidate_button.setCheckable(True)
        self.candidate_group.addButton(self.fast_candidate_button, 0)
        self.candidate_group.addButton(self.best_candidate_button, 1)
        candidate_row.addWidget(self.fast_candidate_button)
        candidate_row.addWidget(self.best_candidate_button)
        quality_grid.addLayout(candidate_row, 0, 1, 1, 2)

        score_label = QLabel("最低预测质量")
        score_label.setToolTip("最佳候选低于该分数时不显示预览；0 表示不过滤。")
        quality_grid.addWidget(score_label, 1, 0)
        self.score_slider = QSlider(Qt.Orientation.Horizontal)
        self.score_slider.setRange(0, 20)
        self.score_slider.setSingleStep(1)
        quality_grid.addWidget(self.score_slider, 1, 1)
        self.score_spin = QDoubleSpinBox()
        self.score_spin.setRange(0.0, 1.0)
        self.score_spin.setDecimals(2)
        self.score_spin.setSingleStep(0.05)
        self.score_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.score_spin.setFixedWidth(102)
        quality_grid.addWidget(self.score_spin, 1, 2)
        root.addLayout(quality_grid)
        root.addWidget(self._separator())

        result_title = QLabel("结果处理")
        result_title.setObjectName("samAdvancedSectionTitle")
        root.addWidget(result_title)
        result_grid = QGridLayout()
        result_grid.setContentsMargins(0, 0, 0, 0)
        result_grid.setHorizontalSpacing(12)
        result_grid.setVerticalSpacing(12)

        area_label = QLabel("最小掩码面积")
        area_label.setToolTip("小于该像素面积的掩码会被视为噪声并过滤；滑块采用对数刻度。")
        result_grid.addWidget(area_label, 0, 0)
        self.area_slider = QSlider(Qt.Orientation.Horizontal)
        self.area_slider.setRange(0, self._AREA_SLIDER_STEPS)
        self.area_slider.setSingleStep(1)
        result_grid.addWidget(self.area_slider, 0, 1)
        self.area_spin = QSpinBox()
        self.area_spin.setRange(self._MINIMUM_AREA, self._MAXIMUM_AREA)
        self.area_spin.setSuffix(" px²")
        self.area_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.area_spin.setFixedWidth(102)
        result_grid.addWidget(
            self.area_spin,
            0,
            2,
        )

        simplify_label = QLabel("轮廓简化比例")
        simplify_label.setToolTip("比例越高，多边形顶点越少；矩形和有向矩形不受影响。")
        result_grid.addWidget(simplify_label, 1, 0)
        self.simplify_slider = QSlider(Qt.Orientation.Horizontal)
        self.simplify_slider.setRange(0, 30)
        self.simplify_slider.setSingleStep(1)
        result_grid.addWidget(self.simplify_slider, 1, 1)
        self.simplify_spin = QDoubleSpinBox()
        self.simplify_spin.setRange(0.0, 1.5)
        self.simplify_spin.setDecimals(2)
        self.simplify_spin.setSingleStep(0.05)
        self.simplify_spin.setSuffix(" %")
        self.simplify_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.simplify_spin.setFixedWidth(102)
        result_grid.addWidget(self.simplify_spin, 1, 2)
        root.addLayout(result_grid)
        root.addStretch(1)

        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        self.reset_button = QPushButton("恢复默认")
        self.reset_button.setObjectName("samAdvancedReset")
        self.reset_button.clicked.connect(self.reset_defaults)
        footer.addWidget(self.reset_button)
        footer.addStretch(1)
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        footer.addWidget(cancel_button)
        self.save_button = QPushButton("保存")
        self.save_button.setObjectName("samAdvancedSave")
        self.save_button.setDefault(True)
        self.save_button.clicked.connect(self.accept)
        footer.addWidget(self.save_button)
        root.addLayout(footer)

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
        self._apply_style()

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
        fraction = max(0.0, min(1.0, float(slider_value) / cls._AREA_SLIDER_STEPS))
        minimum_log = log(cls._MINIMUM_AREA)
        maximum_log = log(cls._MAXIMUM_AREA)
        return round(exp(minimum_log + (maximum_log - minimum_log) * fraction))

    @classmethod
    def _slider_from_area(cls, area: int) -> int:
        bounded = max(cls._MINIMUM_AREA, min(cls._MAXIMUM_AREA, int(area)))
        fraction = (log(bounded) - log(cls._MINIMUM_AREA)) / (
            log(cls._MAXIMUM_AREA) - log(cls._MINIMUM_AREA)
        )
        return round(fraction * cls._AREA_SLIDER_STEPS)

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
        QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(selected_model.checkpoint_path.parent.resolve()))
        )

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

    @staticmethod
    def _separator() -> QFrame:
        separator = QFrame()
        separator.setObjectName("samAdvancedSeparator")
        separator.setFixedHeight(1)
        return separator

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QDialog#samAdvancedDialog { background: #FFFFFF; color: #14233A; }
            QLabel { color: #14233A; font-size: 14px; }
            QLabel#samAdvancedCaption { color: #69798A; }
            QLabel#samAdvancedSectionTitle { font-size: 16px; font-weight: 600; }
            QFrame#samAdvancedSeparator { background: #E2E8EF; border: 0; }
            QPushButton { min-height: 34px; padding: 0 16px; border: 1px solid #CFD9E3;
                border-radius: 6px; background: #FFFFFF; color: #24364B; }
            QPushButton:hover { background: #F4F8FB; border-color: #AEBECD; }
            QPushButton#samSegmentLeft, QPushButton#samSegmentRight { min-height: 32px;
                padding: 0 12px; border-radius: 0; }
            QPushButton#samSegmentLeft { border-top-left-radius: 6px;
                border-bottom-left-radius: 6px; }
            QPushButton#samSegmentRight { border-left: 0; border-top-right-radius: 6px;
                border-bottom-right-radius: 6px; }
            QPushButton#samSegmentLeft:checked, QPushButton#samSegmentRight:checked {
                background: #E8F7F0; border-color: #20A66A; color: #147548; font-weight: 600; }
            QPushButton#samAdvancedReset { background: transparent; color: #52667A; }
            QPushButton#samAdvancedSave { background: #15965C; border-color: #15965C;
                color: #FFFFFF; font-weight: 600; min-width: 72px; }
            QPushButton#samAdvancedSave:hover { background: #117E4D; border-color: #117E4D; }
            QComboBox#samAdvancedModelCombo { min-height: 32px; border: 1px solid #CFD9E3;
                border-radius: 6px; padding: 0 8px; background: #FFFFFF; color: #14233A; }
            QComboBox#samAdvancedModelCombo:focus { border-color: #15965C; }
            QPushButton#samOpenModelFolder { min-height: 32px; padding: 0 8px;
                border: 1px solid #CFD9E3; border-radius: 6px;
                background: #FFFFFF; color: #24364B; }
            QPushButton#samOpenModelFolder:hover { background: #F4F8FB;
                border-color: #AEBECD; }
            QPushButton#samOpenModelFolder:disabled { background: #F3F5F7;
                color: #9AA7B4; border-color: #DDE4EA; }
            QSpinBox, QDoubleSpinBox { min-height: 32px; border: 1px solid #CFD9E3;
                border-radius: 6px; padding: 0 8px;
                background: #FFFFFF; }
            QSpinBox:focus, QDoubleSpinBox:focus { border-color: #15965C; }
            QSlider::groove:horizontal { height: 4px; border-radius: 2px; background: #DCE5EC; }
            QSlider::sub-page:horizontal { background: #20A66A; border-radius: 2px; }
            QSlider::handle:horizontal { width: 16px; margin: -6px 0; border-radius: 8px;
                background: #FFFFFF; border: 2px solid #15965C; }
            """
        )

__all__ = ["SAM_ASSIST_PARAMETER_DEFAULTS", "SamAdvancedSettingsDialog"]
