from __future__ import annotations

from src.services.data_ops import display_project_path, resolve_project_path
from src.ui.shared.assets import load_sam_assist_icon
from src.ui.shared.widgets.toggle_switch import AnimatedToggleSwitch
from src.shared.qt import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSizePolicy,
    Qt,
    QVBoxLayout,
    QWidget,
)


def build_dialog_ui(
    dialog,
    line_expand_enabled: bool,
    selected_sam_model: str = "",
) -> None:
    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(16, 12, 16, 16)
    layout.setSpacing(0)
    
    sam_widget = QWidget()
    sam_layout = QVBoxLayout(sam_widget)
    sam_layout.setContentsMargins(4, 0, 4, 12)
    sam_layout.setSpacing(8)
    sam_header = QHBoxLayout()
    sam_header.setContentsMargins(0, 0, 0, 0)
    sam_icon = QLabel()
    sam_icon.setFixedSize(24, 24)
    sam_icon.setPixmap(load_sam_assist_icon().pixmap(22, 22))
    sam_header.addWidget(sam_icon)
    sam_header.addWidget(QLabel("SAM 智能标注"))
    sam_header.addStretch(1)
    dialog.sam_switch = AnimatedToggleSwitch()
    dialog.sam_switch.setToolTip("开启或关闭 SAM 智能标注")
    sam_header.addWidget(dialog.sam_switch)
    sam_layout.addLayout(sam_header)
    model_row = QHBoxLayout()
    model_row.setContentsMargins(0, 0, 0, 0)
    model_row.setSpacing(8)
    dialog.sam_model_combo = QComboBox()
    dialog.sam_model_combo.setSizePolicy(
        QSizePolicy.Policy.Ignored,
        QSizePolicy.Policy.Fixed,
    )
    if dialog.sam_models:
        for model in dialog.sam_models:
            dialog.sam_model_combo.addItem(model.display_name, model.key)
        selected_index = dialog.sam_model_combo.findData(selected_sam_model)
        dialog.sam_model_combo.setCurrentIndex(max(0, selected_index))
    else:
        dialog.sam_model_combo.addItem("未找到可用的 SAM 模型")
        dialog.sam_model_combo.setEnabled(False)
        dialog.sam_switch.setEnabled(False)
        dialog.sam_enabled = False
    dialog.sam_switch.setChecked(dialog.sam_enabled)
    dialog.sam_switch.toggled.connect(dialog._set_sam_enabled)
    dialog.sam_model_combo.currentIndexChanged.connect(dialog._select_sam_model)
    model_row.addWidget(dialog.sam_model_combo, 1)
    dialog.sam_advanced_button = QPushButton("高级")
    dialog.sam_advanced_button.setObjectName("samAdvancedButton")
    dialog.sam_advanced_button.setFixedSize(50, 36)
    dialog.sam_advanced_button.setCursor(Qt.CursorShape.PointingHandCursor)
    dialog.sam_advanced_button.setToolTip("打开 SAM 高级参数设置")
    selected_model_supported = dialog._selected_sam_supports_assist()
    dialog.sam_advanced_button.setEnabled(selected_model_supported)
    dialog.sam_switch.setEnabled(selected_model_supported)
    if not selected_model_supported and dialog.sam_enabled:
        dialog.sam_enabled = False
        dialog.sam_switch.blockSignals(True)
        dialog.sam_switch.setChecked(False)
        dialog.sam_switch.blockSignals(False)
    dialog.sam_advanced_button.clicked.connect(dialog._open_sam_advanced_settings)
    model_row.addWidget(dialog.sam_advanced_button)
    sam_layout.addLayout(model_row)
    layout.addWidget(sam_widget)
    
    list_frame = QFrame()
    list_frame.setObjectName("drawShapeList")
    list_layout = QVBoxLayout(list_frame)
    list_layout.setContentsMargins(0, 0, 0, 0)
    list_layout.setSpacing(0)
    
    edit_button = QPushButton("编辑")
    edit_button.setMinimumHeight(44)
    edit_button.setCursor(Qt.CursorShape.PointingHandCursor)
    edit_button.setObjectName("drawShapeEditOption")
    edit_button.clicked.connect(lambda: dialog.choose_shape("select"))
    list_layout.addWidget(edit_button)
    divider = QFrame()
    divider.setObjectName("drawShapeDivider")
    divider.setFixedHeight(2)
    list_layout.addWidget(divider)
    options = [
        ("矩形框", "rect"),
        ("有向矩形", "obb_single"),
        ("镜像有向矩形", "obb_mirror"),
        ("多边形", "polygon"),
        ("圆形", "circle"),
    ]
    if line_expand_enabled:
        options.append(("直线扩展", "line_expand"))
    dialog._options = options
    dialog._shape_buttons = {}
    
    for index, (text, value) in enumerate(options):
        button = QPushButton(text)
        button.setMinimumHeight(44)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        if len(options) == 1:
            object_name = "drawShapeOptionSingle"
        elif index == 0:
            object_name = "drawShapeOptionFirst"
        elif index == len(options) - 1:
            object_name = "drawShapeOptionLast"
        else:
            object_name = "drawShapeOption"
        button.setObjectName(object_name)
        button.clicked.connect(lambda _checked=False, shape=value: dialog.choose_shape(shape))
        list_layout.addWidget(button)
        dialog._shape_buttons[value] = button
    layout.addWidget(list_frame)
    layout.addStretch(1)
    dialog.setStyleSheet(
        """
        QFrame#drawShapeList {
            background: #FFFFFF;
            border: 1px solid #D9E3EC;
            border-radius: 10px;
        }
        QFrame#drawShapeDivider {
            background: #D9E3EC;
        }
        QPushButton#drawShapeEditOption {
            background: #FFFFFF;
            color: #14233A;
            border: 0;
            border-top-left-radius: 10px;
            border-top-right-radius: 10px;
            padding: 10px 14px;
            text-align: center;
            font-size: 15px;
        }
        QPushButton#drawShapeEditOption:hover {
            background: #F5F8FB;
        }
        QPushButton#drawShapeOptionSingle,
        QPushButton#drawShapeOptionFirst,
        QPushButton#drawShapeOption,
        QPushButton#drawShapeOptionLast {
            background: #FFFFFF;
            color: #14233A;
            border: 0;
            border-radius: 0;
            padding: 10px 14px;
            text-align: center;
            font-size: 15px;
        }
        QPushButton#drawShapeOptionSingle {
            border-radius: 10px;
        }
        QPushButton#drawShapeOptionFirst {
            border-top-left-radius: 0;
            border-top-right-radius: 0;
            border-bottom: 1px solid #E6EDF4;
        }
        QPushButton#drawShapeOption {
            border-bottom: 1px solid #E6EDF4;
        }
        QPushButton#drawShapeOptionLast {
            border-bottom-left-radius: 10px;
            border-bottom-right-radius: 10px;
        }
        QPushButton#drawShapeOptionSingle:hover,
        QPushButton#drawShapeOptionFirst:hover,
        QPushButton#drawShapeOption:hover,
        QPushButton#drawShapeOptionLast:hover {
            background: #F5F8FB;
        }
        QPushButton#drawShapeOptionSingle:disabled,
        QPushButton#drawShapeOptionFirst:disabled,
        QPushButton#drawShapeOption:disabled,
        QPushButton#drawShapeOptionLast:disabled {
            background: #F3F5F7;
            color: #9AA7B4;
        }
        QPushButton#samAdvancedButton {
            background: #FFFFFF;
            color: #24364B;
            border: 1px solid #CFD9E3;
            border-radius: 6px;
            padding: 0 8px;
            font-size: 14px;
        }
        QPushButton#samAdvancedButton:hover {
            background: #F4F8FB;
            border-color: #AEBECD;
        }
        QPushButton#samAdvancedButton:disabled {
            background: #F3F5F7;
            color: #9AA7B4;
            border-color: #DDE4EA;
        }
        """
    )

    dialog._refresh_sam_shape_availability()

__all__ = ["build_dialog_ui"]
