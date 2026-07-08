from __future__ import annotations

from src.ui.shared.forms import FormPageMixin
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
    Qt,
    QVBoxLayout,
)


class AnnotationSettingsDialog(FormPageMixin, QDialog):
    def __init__(
        self,
        enabled: bool,
        pixels: int,
        auto_save: bool,
        auto_convert_yolo: bool,
        show_yolo_save_in_context_menu: bool,
        continuous_draw: bool,
        quick_draw: bool,
        yolo_dir: str,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("更多设置")
        self.resize(420, 380)
        layout = QVBoxLayout(self)
        self.auto_save_check = QCheckBox("自动保存 Labelme JSON")
        self.auto_save_check.setChecked(bool(auto_save))
        layout.addWidget(self.auto_save_check)
        self.auto_convert_check = QCheckBox("自动转换为 YOLO 格式")
        self.auto_convert_check.setChecked(bool(auto_convert_yolo))
        layout.addWidget(self.auto_convert_check)
        show_yolo_box, self.show_yolo_context_check = self.checkbox_with_help(
            "右键显示保存YOLO标注",
            bool(show_yolo_save_in_context_menu),
            help_text="开启后主界面右键菜单按需分别显示“保存Labelme标注”和“保存YOLO标注”；关闭后只显示“保存”，默认保存 Labelme 标注。",
        )
        layout.addWidget(show_yolo_box)
        continuous_box, self.continuous_draw_check = self.checkbox_with_help(
            "开启连续标注",
            bool(continuous_draw),
            help_text="开启后完成一个标注会继续保持当前绘制类型；关闭后每次完成标注都会自动回到选择模式。",
        )
        layout.addWidget(continuous_box)
        quick_box, self.quick_draw_check = self.checkbox_with_help(
            "开启快捷标注",
            bool(quick_draw),
            help_text="开启后矩形框、圆形、直线扩展支持拖动后松开直接完成；关闭后改为通过多次点击确认。",
        )
        layout.addWidget(quick_box)
        layout.addWidget(QLabel("YOLO 标注文件夹"))
        yolo_row = QHBoxLayout()
        self.yolo_dir_edit = QLineEdit(yolo_dir)
        yolo_row.addWidget(self.yolo_dir_edit, 1)
        choose_btn = QPushButton("选择")
        choose_btn.clicked.connect(self.choose_yolo_dir)
        yolo_row.addWidget(choose_btn)
        layout.addLayout(yolo_row)
        self.enable_combo = QComboBox()
        self.enable_combo.addItems(["关闭直线标注", "开启直线标注"])
        self.enable_combo.setCurrentIndex(1 if enabled else 0)
        line_label_box, self.line_expand_label, _icon = self._caption_widget(
            "直线标注",
            help_text="开启后可在标注类型中使用直线扩展；关闭后该绘制类型不会显示。",
        )
        layout.addWidget(line_label_box)
        layout.addWidget(self.enable_combo)
        self.pixel_spin = QSpinBox()
        self.pixel_spin.setRange(1, 200)
        self.pixel_spin.setValue(max(1, int(pixels)))
        pixel_label_box, self.line_expand_pixels_label, _icon = self._caption_widget(
            "直线扩展像素",
            help_text="设置直线扩展生成旋转矩形时，沿线段两侧扩展的像素宽度。",
        )
        layout.addWidget(pixel_label_box)
        layout.addWidget(self.pixel_spin)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def help_icons_enabled(self) -> bool:
        parent = self.parent()
        if parent is not None and hasattr(parent, "help_icons_enabled"):
            return bool(parent.help_icons_enabled())
        return True

    def refresh_help_icon_visibility(self) -> None:
        for label in self.findChildren(QLabel):
            self._refresh_help_target(label)
        for check in self.findChildren(QCheckBox):
            self._refresh_help_target(check)

    def choose_yolo_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "选择 YOLO 标注文件夹", self.yolo_dir_edit.text().strip()
        )
        if directory:
            self.yolo_dir_edit.setText(directory)

    def values(self) -> tuple[bool, int, bool, bool, bool, bool, bool, str]:
        return (
            self.enable_combo.currentIndex() == 1,
            int(self.pixel_spin.value()),
            self.auto_save_check.isChecked(),
            self.auto_convert_check.isChecked(),
            self.show_yolo_context_check.isChecked(),
            self.continuous_draw_check.isChecked(),
            self.quick_draw_check.isChecked(),
            self.yolo_dir_edit.text().strip(),
        )


class DrawShapeDialog(QDialog):
    def __init__(self, line_expand_enabled: bool, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择标注类型")
        self.resize(220, 330 if line_expand_enabled else 286)
        self.selected_shape = "rect"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        title_label = QLabel("请选择要绘制的标注类型")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
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

        list_frame = QFrame()
        list_frame.setObjectName("drawShapeList")
        list_layout = QVBoxLayout(list_frame)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(0)
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
        layout.addWidget(list_frame)
        layout.addStretch(1)
        self.setStyleSheet(
            """
            QFrame#drawShapeList {
                background: #FFFFFF;
                border: 1px solid #D9E3EC;
                border-radius: 10px;
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
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
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
            """
        )

    def choose_shape(self, shape: str) -> None:
        self.selected_shape = shape
        self.accept()


class ClassManagerDialog(QDialog):
    def __init__(self, class_names: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("管理类别")
        self.resize(360, 420)
        self.class_names = list(class_names)
        layout = QVBoxLayout(self)
        self.listing = QListWidget()
        layout.addWidget(self.listing, 1)
        row = QHBoxLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("类别名称")
        row.addWidget(self.name_edit, 1)
        add_btn = QPushButton("新增")
        add_btn.clicked.connect(self.add_class)
        row.addWidget(add_btn)
        rename_btn = QPushButton("重命名")
        rename_btn.clicked.connect(self.rename_class)
        row.addWidget(rename_btn)
        delete_btn = QPushButton("删除")
        delete_btn.clicked.connect(self.delete_class)
        row.addWidget(delete_btn)
        layout.addLayout(row)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.listing.currentRowChanged.connect(self.sync_name_edit)
        self.refresh()

    def sync_name_edit(self, row: int) -> None:
        if 0 <= row < len(self.class_names):
            self.name_edit.setText(self.class_names[row])

    def refresh(self) -> None:
        current = self.listing.currentRow()
        self.listing.clear()
        for index, name in enumerate(self.class_names):
            self.listing.addItem(f"{index} : {name}")
        if self.class_names:
            self.listing.setCurrentRow(min(max(current, 0), len(self.class_names) - 1))

    def add_class(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            return
        if name in self.class_names:
            QMessageBox.information(self, "管理类别", "类别名称已存在。")
            return
        self.class_names.append(name)
        self.refresh()
        self.listing.setCurrentRow(len(self.class_names) - 1)

    def rename_class(self) -> None:
        row = self.listing.currentRow()
        name = self.name_edit.text().strip()
        if row < 0 or not name:
            return
        if name in self.class_names and self.class_names[row] != name:
            QMessageBox.information(self, "管理类别", "类别名称已存在。")
            return
        self.class_names[row] = name
        self.refresh()
        self.listing.setCurrentRow(row)

    def delete_class(self) -> None:
        row = self.listing.currentRow()
        if row < 0:
            return
        if len(self.class_names) <= 1:
            QMessageBox.information(self, "管理类别", "至少保留一个类别。")
            return
        del self.class_names[row]
        self.refresh()


