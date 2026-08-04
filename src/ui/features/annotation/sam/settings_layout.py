from __future__ import annotations

from src.shared.qt import (
    QAbstractSpinBox,
    QButtonGroup,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    Qt,
    QVBoxLayout,
)


def build_model_section(dialog, root: QVBoxLayout) -> None:
    model_row = QHBoxLayout()
    model_row.setContentsMargins(0, 0, 0, 0)
    model_caption = QLabel("当前模型")
    model_caption.setObjectName("samAdvancedCaption")
    model_row.addWidget(model_caption)
    dialog.model_combo = QComboBox()
    dialog.model_combo.setObjectName("samAdvancedModelCombo")
    dialog.model_combo.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
    for model in dialog.sam_models:
        dialog.model_combo.addItem(model.display_name, model.key)
    selected_index = dialog.model_combo.findData(dialog.selected_model_key_value)
    if selected_index < 0 and dialog.model_name:
        selected_index = dialog.model_combo.findText(dialog.model_name)
    if selected_index >= 0:
        dialog.model_combo.setCurrentIndex(selected_index)
    elif not dialog.sam_models:
        dialog.model_combo.addItem(str(dialog.model_name or "未选择"))
    dialog.model_combo.setEnabled(bool(dialog.sam_models))
    model_row.addWidget(dialog.model_combo, 1)
    dialog.open_model_folder_button = QPushButton("打开文件夹")
    dialog.open_model_folder_button.setObjectName("samOpenModelFolder")
    dialog.open_model_folder_button.setToolTip("打开当前模型所在文件夹")
    dialog.open_model_folder_button.setFixedWidth(104)
    dialog.open_model_folder_button.clicked.connect(dialog._open_model_folder)
    dialog.open_model_folder_button.setEnabled(bool(dialog.sam_models))
    model_row.addWidget(dialog.open_model_folder_button)
    root.addLayout(model_row)
    root.addWidget(separator())


def build_quality_section(dialog, root: QVBoxLayout) -> None:
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
    dialog.candidate_group = QButtonGroup(dialog)
    dialog.candidate_group.setExclusive(True)
    dialog.fast_candidate_button = QPushButton("快速单结果")
    dialog.fast_candidate_button.setObjectName("samSegmentLeft")
    dialog.fast_candidate_button.setCheckable(True)
    dialog.best_candidate_button = QPushButton("三候选优选")
    dialog.best_candidate_button.setObjectName("samSegmentRight")
    dialog.best_candidate_button.setCheckable(True)
    dialog.candidate_group.addButton(dialog.fast_candidate_button, 0)
    dialog.candidate_group.addButton(dialog.best_candidate_button, 1)
    candidate_row.addWidget(dialog.fast_candidate_button)
    candidate_row.addWidget(dialog.best_candidate_button)
    quality_grid.addLayout(candidate_row, 0, 1, 1, 2)

    score_label = QLabel("最低预测质量")
    score_label.setToolTip("最佳候选低于该分数时不显示预览；0 表示不过滤。")
    quality_grid.addWidget(score_label, 1, 0)
    dialog.score_slider = QSlider(Qt.Orientation.Horizontal)
    dialog.score_slider.setRange(0, 20)
    dialog.score_slider.setSingleStep(1)
    quality_grid.addWidget(dialog.score_slider, 1, 1)
    dialog.score_spin = QDoubleSpinBox()
    dialog.score_spin.setRange(0.0, 1.0)
    dialog.score_spin.setDecimals(2)
    dialog.score_spin.setSingleStep(0.05)
    dialog.score_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
    dialog.score_spin.setFixedWidth(102)
    quality_grid.addWidget(dialog.score_spin, 1, 2)
    root.addLayout(quality_grid)
    root.addWidget(separator())


def build_result_section(dialog, root: QVBoxLayout) -> None:
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
    dialog.area_slider = QSlider(Qt.Orientation.Horizontal)
    dialog.area_slider.setRange(0, dialog.area_slider_steps)
    dialog.area_slider.setSingleStep(1)
    result_grid.addWidget(dialog.area_slider, 0, 1)
    dialog.area_spin = QSpinBox()
    dialog.area_spin.setRange(dialog.minimum_area, dialog.maximum_area)
    dialog.area_spin.setSuffix(" px²")
    dialog.area_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
    dialog.area_spin.setFixedWidth(102)
    result_grid.addWidget(dialog.area_spin, 0, 2)

    simplify_label = QLabel("轮廓简化比例")
    simplify_label.setToolTip("比例越高，多边形顶点越少；矩形和有向矩形不受影响。")
    result_grid.addWidget(simplify_label, 1, 0)
    dialog.simplify_slider = QSlider(Qt.Orientation.Horizontal)
    dialog.simplify_slider.setRange(0, 30)
    dialog.simplify_slider.setSingleStep(1)
    result_grid.addWidget(dialog.simplify_slider, 1, 1)
    dialog.simplify_spin = QDoubleSpinBox()
    dialog.simplify_spin.setRange(0.0, 1.5)
    dialog.simplify_spin.setDecimals(2)
    dialog.simplify_spin.setSingleStep(0.05)
    dialog.simplify_spin.setSuffix(" %")
    dialog.simplify_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
    dialog.simplify_spin.setFixedWidth(102)
    result_grid.addWidget(dialog.simplify_spin, 1, 2)
    root.addLayout(result_grid)


def build_footer(dialog, root: QVBoxLayout) -> None:
    root.addStretch(1)
    footer = QHBoxLayout()
    footer.setContentsMargins(0, 0, 0, 0)
    dialog.reset_button = QPushButton("恢复默认")
    dialog.reset_button.setObjectName("samAdvancedReset")
    dialog.reset_button.clicked.connect(dialog.reset_defaults)
    footer.addWidget(dialog.reset_button)
    footer.addStretch(1)
    cancel_button = QPushButton("取消")
    cancel_button.clicked.connect(dialog.reject)
    footer.addWidget(cancel_button)
    dialog.save_button = QPushButton("保存")
    dialog.save_button.setObjectName("samAdvancedSave")
    dialog.save_button.setDefault(True)
    dialog.save_button.clicked.connect(dialog.accept)
    footer.addWidget(dialog.save_button)
    root.addLayout(footer)


def separator() -> QFrame:
    separator = QFrame()
    separator.setObjectName("samAdvancedSeparator")
    separator.setFixedHeight(1)
    return separator


def apply_style(dialog) -> None:
    dialog.setStyleSheet(
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
            border-radius: 6px; padding: 0 8px; background: #FFFFFF; }
        QSpinBox:focus, QDoubleSpinBox:focus { border-color: #15965C; }
        QSlider::groove:horizontal { height: 4px; border-radius: 2px; background: #DCE5EC; }
        QSlider::sub-page:horizontal { background: #20A66A; border-radius: 2px; }
        QSlider::handle:horizontal { width: 16px; margin: -6px 0; border-radius: 8px;
            background: #FFFFFF; border: 2px solid #15965C; }
        """
    )


__all__ = [
    "apply_style",
    "build_footer",
    "build_model_section",
    "build_quality_section",
    "build_result_section",
    "separator",
]
