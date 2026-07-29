from __future__ import annotations

from pathlib import Path

from src.services.data_ops import display_project_path, resolve_project_path
from src.ui.shared.forms import FormPageMixin
from src.ui.shared.assets import load_sam_assist_icon
from src.ui.shared.widgets.toggle_switch import AnimatedToggleSwitch
from src.ui.features.annotation.sam.settings_dialog import SamAdvancedSettingsDialog
from src.shared.qt import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
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


class DrawShapeDialog(QDialog):
    def __init__(
        self,
        line_expand_enabled: bool,
        parent=None,
        *,
        sam_models=None,
        selected_sam_model: str = "",
        sam_enabled: bool = False,
        sam_toggle_callback=None,
        sam_model_callback=None,
        sam_settings=None,
        sam_settings_callback=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("选择标注类型")
        self.resize(240, 424 if line_expand_enabled else 380)
        self.selected_shape = "rect"
        self.sam_models = list(sam_models or [])
        self.sam_enabled = bool(sam_enabled)
        self.sam_toggle_callback = sam_toggle_callback
        self.sam_model_callback = sam_model_callback
        self.sam_settings = dict(sam_settings or {})
        self.sam_settings_callback = sam_settings_callback
        layout = QVBoxLayout(self)
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
        self.sam_switch = AnimatedToggleSwitch()
        self.sam_switch.setToolTip("开启或关闭 SAM 智能标注")
        sam_header.addWidget(self.sam_switch)
        sam_layout.addLayout(sam_header)
        model_row = QHBoxLayout()
        model_row.setContentsMargins(0, 0, 0, 0)
        model_row.setSpacing(8)
        self.sam_model_combo = QComboBox()
        self.sam_model_combo.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Fixed,
        )
        if self.sam_models:
            for model in self.sam_models:
                self.sam_model_combo.addItem(model.display_name, model.key)
            selected_index = self.sam_model_combo.findData(selected_sam_model)
            self.sam_model_combo.setCurrentIndex(max(0, selected_index))
        else:
            self.sam_model_combo.addItem("未找到可用的 SAM 模型")
            self.sam_model_combo.setEnabled(False)
            self.sam_switch.setEnabled(False)
            self.sam_enabled = False
        self.sam_switch.setChecked(self.sam_enabled)
        self.sam_switch.toggled.connect(self._set_sam_enabled)
        self.sam_model_combo.currentIndexChanged.connect(self._select_sam_model)
        model_row.addWidget(self.sam_model_combo, 1)
        self.sam_advanced_button = QPushButton("高级")
        self.sam_advanced_button.setObjectName("samAdvancedButton")
        self.sam_advanced_button.setFixedSize(50, 36)
        self.sam_advanced_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sam_advanced_button.setToolTip("打开 SAM 高级参数设置")
        selected_model_supported = self._selected_sam_supports_assist()
        self.sam_advanced_button.setEnabled(selected_model_supported)
        self.sam_switch.setEnabled(selected_model_supported)
        if not selected_model_supported and self.sam_enabled:
            self.sam_enabled = False
            self.sam_switch.blockSignals(True)
            self.sam_switch.setChecked(False)
            self.sam_switch.blockSignals(False)
        self.sam_advanced_button.clicked.connect(self._open_sam_advanced_settings)
        model_row.addWidget(self.sam_advanced_button)
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
        edit_button.clicked.connect(lambda: self.choose_shape("select"))
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
        self._options = options
        self._shape_buttons = {}

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
            button.clicked.connect(lambda _checked=False, shape=value: self.choose_shape(shape))
            list_layout.addWidget(button)
            self._shape_buttons[value] = button
        layout.addWidget(list_frame)
        layout.addStretch(1)
        self.setStyleSheet(
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
        self._refresh_sam_shape_availability()

    @property
    def selected_sam_model(self) -> str:
        return str(self.sam_model_combo.currentData() or "")

    def _set_sam_enabled(self, enabled: bool) -> None:
        actual = bool(enabled)
        if self.sam_toggle_callback is not None:
            actual = bool(self.sam_toggle_callback(actual))
        self.sam_enabled = actual
        if self.sam_switch.isChecked() != actual:
            self.sam_switch.blockSignals(True)
            self.sam_switch.setChecked(actual)
            self.sam_switch.blockSignals(False)
        self._refresh_sam_shape_availability()

    def _select_sam_model(self, _index: int) -> None:
        supported = self._selected_sam_supports_assist()
        if not supported and self.sam_enabled:
            self._set_sam_enabled(False)
        if self.sam_model_callback is not None and self.selected_sam_model:
            self.sam_model_callback(self.selected_sam_model)
        self.sam_switch.setEnabled(supported)
        self.sam_advanced_button.setEnabled(supported)

    def _selected_sam_supports_assist(self) -> bool:
        selected_key = self.selected_sam_model
        selected = next(
            (model for model in self.sam_models if model.key == selected_key),
            None,
        )
        return bool(selected is not None and selected.supports_assist)

    def _open_sam_advanced_settings(self) -> None:
        dialog = SamAdvancedSettingsDialog(
            self.sam_settings,
            self.sam_model_combo.currentText(),
            self,
            sam_models=self.sam_models,
            selected_model_key=self.selected_sam_model,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        selected_model_key = dialog.selected_model_key()
        if selected_model_key and selected_model_key != self.selected_sam_model:
            selected_index = self.sam_model_combo.findData(selected_model_key)
            if selected_index >= 0:
                self.sam_model_combo.setCurrentIndex(selected_index)
        values = dialog.values()
        if self.sam_settings_callback is not None:
            applied = self.sam_settings_callback(values)
            if isinstance(applied, dict):
                values = applied
        self.sam_settings = dict(values)

    def _refresh_sam_shape_availability(self) -> None:
        supported = {"rect", "obb_single", "obb_mirror", "polygon"}
        for shape, button in self._shape_buttons.items():
            button.setEnabled(not self.sam_enabled or shape in supported)

    def choose_shape(self, shape: str) -> None:
        if self.sam_enabled and shape not in {"select", "rect", "obb_single", "obb_mirror", "polygon"}:
            return
        self.selected_shape = shape
        self.accept()



