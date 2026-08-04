from __future__ import annotations

from src.shared.qt import (
    QAbstractSpinBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QSizePolicy,
    QToolButton,
    Qt,
    QVBoxLayout,
    QWidget,
)


def build_model_card(dialog):
    model_card = QFrame()
    model_card.setObjectName("card")
    model_layout = QVBoxLayout(model_card)
    model_layout.setContentsMargins(12, 10, 12, 10)
    model_layout.setSpacing(8)
    title = QLabel("模型与参数")
    title.setObjectName("sectionTitle")
    model_layout.addWidget(title)
    
    model_row = QHBoxLayout()
    model_row.setContentsMargins(0, 0, 0, 0)
    model_row.setSpacing(8)
    model_label = QLabel("模型文件:")
    model_label.setObjectName("annotationPathLabel")
    model_row.addWidget(model_label)
    dialog.model_combo = QComboBox()
    dialog.model_combo.setEditable(True)
    dialog.model_combo.lineEdit().setStyleSheet(
        "QLineEdit { padding: 0; border: 0; background: transparent; }"
    )
    preferred_model = dialog._preferred_model_text()
    dialog.refresh_model_choices(str(preferred_model) if preferred_model else "")
    model_row.addWidget(dialog.model_combo, 1)
    browse_btn = QPushButton("浏览")
    browse_btn.clicked.connect(dialog.choose_model)
    model_row.addWidget(browse_btn)
    model_layout.addLayout(model_row)
    
    dialog.threshold_widget = QWidget()
    threshold_row = QHBoxLayout(dialog.threshold_widget)
    threshold_row.setContentsMargins(0, 0, 0, 0)
    threshold_row.setSpacing(8)
    conf_label = QLabel("置信度:")
    conf_label.setObjectName("annotationPathLabel")
    threshold_row.addWidget(conf_label)
    dialog.conf_spin = QDoubleSpinBox()
    dialog.conf_spin.setRange(0.0, 1.0)
    dialog.conf_spin.setSingleStep(0.05)
    dialog.conf_spin.setDecimals(2)
    dialog.conf_spin.setValue(dialog.saved_confidence)
    threshold_row.addWidget(dialog.conf_spin)
    iou_label = QLabel("IoU:")
    iou_label.setObjectName("annotationPathLabel")
    threshold_row.addSpacing(12)
    threshold_row.addWidget(iou_label)
    dialog.iou_spin = QDoubleSpinBox()
    dialog.iou_spin.setRange(0.0, 1.0)
    dialog.iou_spin.setSingleStep(0.05)
    dialog.iou_spin.setDecimals(2)
    dialog.iou_spin.setValue(dialog.saved_iou)
    threshold_row.addWidget(dialog.iou_spin)
    threshold_row.addStretch(1)
    model_layout.addWidget(dialog.threshold_widget)
    
    dialog.sam3_advanced_toggle = QToolButton()
    dialog.sam3_advanced_toggle.setText("高级参数")
    dialog.sam3_advanced_toggle.setCheckable(True)
    dialog.sam3_advanced_toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    dialog.sam3_advanced_toggle.setArrowType(Qt.ArrowType.RightArrow)
    dialog.sam3_advanced_toggle.toggled.connect(dialog._toggle_sam3_advanced)
    
    shape_row = QHBoxLayout()
    shape_row.setContentsMargins(0, 0, 0, 0)
    shape_row.setSpacing(8)
    dialog.shape_label = QLabel("标注形状:")
    dialog.shape_label.setObjectName("annotationPathLabel")
    shape_row.addWidget(dialog.shape_label)
    dialog.shape_combo = QComboBox()
    dialog.shape_combo.addItem("矩形框", "rect")
    dialog.shape_combo.addItem("有向矩形", "obb")
    dialog.shape_combo.addItem("多边形", "polygon")
    dialog.shape_combo.currentIndexChanged.connect(dialog._on_sam3_shape_changed)
    shape_row.addWidget(dialog.shape_combo, 1)
    shape_row.addWidget(dialog.sam3_advanced_toggle)
    model_layout.addLayout(shape_row)
    
    dialog.sam3_advanced_frame = QFrame()
    advanced_layout = QHBoxLayout(dialog.sam3_advanced_frame)
    advanced_layout.setContentsMargins(0, 0, 0, 0)
    advanced_layout.setSpacing(8)
    min_area_label = QLabel("最小面积:")
    min_area_label.setObjectName("annotationPathLabel")
    advanced_layout.addWidget(min_area_label)
    dialog.sam3_min_area_spin = QSpinBox()
    dialog.sam3_min_area_spin.setRange(1, 100000000)
    dialog.sam3_min_area_spin.setValue(dialog.saved_sam3_min_area)
    advanced_layout.addWidget(dialog.sam3_min_area_spin)
    simplify_label = QLabel("轮廓简化 %:")
    simplify_label.setObjectName("annotationPathLabel")
    advanced_layout.addWidget(simplify_label)
    dialog.sam3_simplify_spin = QDoubleSpinBox()
    dialog.sam3_simplify_spin.setRange(0.0, 10.0)
    dialog.sam3_simplify_spin.setSingleStep(0.1)
    dialog.sam3_simplify_spin.setDecimals(2)
    dialog.sam3_simplify_spin.setButtonSymbols(
        QAbstractSpinBox.ButtonSymbols.NoButtons
    )
    dialog.sam3_simplify_spin.setValue(dialog.saved_sam3_polygon_simplify_ratio * 100.0)
    advanced_layout.addWidget(dialog.sam3_simplify_spin)
    advanced_layout.addStretch(1)
    dialog.sam3_advanced_frame.setVisible(False)
    model_layout.addWidget(dialog.sam3_advanced_frame)
    return model_card


__all__ = ["build_model_card"]
