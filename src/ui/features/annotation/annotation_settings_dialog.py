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
        *,
        load_yolo_when_labelme_missing: bool = False,
        show_annotation_names: bool = False,
        show_canvas_status: bool = True,
        optimize_mirror_edit: bool = False,
    ):
        super().__init__(parent)
        self.setWindowTitle("更多设置")
        self.resize(300, 450)
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        self.auto_save_check = QCheckBox("自动保存 Labelme JSON")
        self.auto_save_check.setChecked(bool(auto_save))
        auto_convert_box, self.auto_convert_check = self.checkbox_with_help(
            "自动转换为 YOLO 格式",
            bool(auto_convert_yolo),
            help_text="开启后保存 Labelme 标注时同步生成或更新同名 YOLO .txt 文件；关闭后不自动转换。",
        )
        load_yolo_box, self.load_yolo_missing_check = self.checkbox_with_help(
            "若无Labelme标注，则自动读取显示YOLO标注",
            bool(load_yolo_when_labelme_missing),
            help_text="开启后当前图片没有 Labelme JSON 时，自动读取同名 YOLO 标注显示；任务类别探测不受此开关影响。",
        )
        show_yolo_box, self.show_yolo_context_check = self.checkbox_with_help(
            "右键显示保存YOLO标注",
            bool(show_yolo_save_in_context_menu),
            help_text="开启后主界面右键菜单按需分别显示“保存Labelme标注”和“保存YOLO标注”；关闭后只显示“保存”，默认保存 Labelme 标注。",
        )
        show_annotation_names_box, self.show_annotation_names_check = self.checkbox_with_help(
            "显示标注名称",
            bool(show_annotation_names),
            help_text="开启后在画布中显示已完成标注的类别名称；关闭后只显示标注图形。",
        )
        show_canvas_status_box, self.show_canvas_status_check = self.checkbox_with_help(
            "显示当前状态",
            bool(show_canvas_status),
            help_text="开启后在数据标注页底部状态栏显示当前状态，例如“当前状态：矩形框”；关闭后隐藏状态栏。",
        )
        continuous_box, self.continuous_draw_check = self.checkbox_with_help(
            "开启连续标注",
            bool(continuous_draw),
            help_text="开启后完成一个标注会继续保持当前绘制类型；关闭后每次完成标注都会自动回到选择模式。",
        )
        quick_box, self.quick_draw_check = self.checkbox_with_help(
            "开启快捷标注",
            bool(quick_draw),
            help_text="开启后矩形框、圆形、直线扩展支持拖动后松开直接完成；关闭后改为通过多次点击确认。",
        )
        optimize_mirror_box, self.optimize_mirror_check = self.checkbox_with_help(
            "优化镜像有向矩形编辑",
            bool(optimize_mirror_edit),
            help_text="开启后编辑镜像有向矩形时显示中心线，只保留中心线端点和两侧宽度控制点。",
        )
        line_label_box, self.line_expand_check = self.checkbox_with_help(
            "开启直线扩展标注",
            bool(enabled),
            help_text="开启后可在标注类型中使用直线扩展；关闭后该绘制类型不会显示。",
        )
        self.line_expand_label = self.line_expand_check

        yolo_setting = QWidget()
        yolo_layout = QVBoxLayout(yolo_setting)
        yolo_layout.setContentsMargins(0, 0, 0, 0)
        yolo_layout.setSpacing(4)
        yolo_layout.addWidget(QLabel("YOLO 标注文件夹"))
        yolo_row = QHBoxLayout()
        yolo_row.setContentsMargins(0, 0, 0, 0)
        project_root = self._project_root()
        display_yolo_dir = (
            display_project_path(yolo_dir, project_root)
            if project_root is not None
            else yolo_dir
        )
        self.yolo_dir_edit = QLineEdit(display_yolo_dir)
        yolo_row.addWidget(self.yolo_dir_edit, 1)
        choose_btn = QPushButton("选择")
        choose_btn.clicked.connect(self.choose_yolo_dir)
        yolo_row.addWidget(choose_btn)
        yolo_layout.addLayout(yolo_row)

        self.pixel_spin = QSpinBox()
        self.pixel_spin.setRange(1, 200)
        self.pixel_spin.setValue(max(1, int(pixels)))
        pixel_label_box, self.line_expand_pixels_label, _icon = self._caption_widget(
            "直线扩展像素",
            help_text="设置直线扩展生成旋转矩形时，沿线段两侧扩展的像素宽度。",
        )
        pixel_setting = QWidget()
        pixel_layout = QVBoxLayout(pixel_setting)
        pixel_layout.setContentsMargins(0, 0, 0, 0)
        pixel_layout.setSpacing(4)
        pixel_layout.addWidget(pixel_label_box)
        pixel_layout.addWidget(self.pixel_spin)

        self._setting_rows = [
            self.auto_save_check,
            auto_convert_box,
            show_yolo_box,
            load_yolo_box,
            show_annotation_names_box,
            show_canvas_status_box,
            continuous_box,
            quick_box,
            optimize_mirror_box,
            line_label_box,
            yolo_setting,
            pixel_setting,
        ]
        for index, setting in enumerate(self._setting_rows):
            if index:
                layout.addStretch(1)
            layout.addWidget(setting)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("确定")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addStretch(1)
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
        project_root = self._project_root()
        current = self.yolo_dir_edit.text().strip()
        if project_root is not None:
            current = resolve_project_path(current, project_root) if current else str(project_root)
        directory = QFileDialog.getExistingDirectory(
            self, "选择 YOLO 标注文件夹", current
        )
        if directory:
            self.yolo_dir_edit.setText(
                display_project_path(directory, project_root)
                if project_root is not None
                else directory
            )

    def _project_root(self) -> Path | None:
        parent = self.parent()
        getter = getattr(parent, "project_root", None)
        if not callable(getter):
            return None
        return Path(getter())

    def values(
        self,
    ) -> tuple[bool, int, bool, bool, bool, bool, bool, bool, str, bool, bool, bool]:
        return (
            self.line_expand_check.isChecked(),
            int(self.pixel_spin.value()),
            self.auto_save_check.isChecked(),
            self.auto_convert_check.isChecked(),
            self.load_yolo_missing_check.isChecked(),
            self.show_yolo_context_check.isChecked(),
            self.continuous_draw_check.isChecked(),
            self.quick_draw_check.isChecked(),
            self.yolo_dir_edit.text().strip(),
            self.show_annotation_names_check.isChecked(),
            self.show_canvas_status_check.isChecked(),
            self.optimize_mirror_check.isChecked(),
        )



