from __future__ import annotations

import traceback
from pathlib import Path

from scr.services.conversion_service import (
    ConversionConfig,
    detect_labelme_classes,
    format_conversion_result,
    preview_conversion,
    run_conversion,
)
from scr.ui.dialogs import ClassMappingDialog
from scr.ui.page_base import BasePage, Card
from scr.ui.qt import (
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

class ConvertTab(BasePage):
    def __init__(self, app):
        super().__init__(app)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        paths = app.settings["paths"]
        dataset = app.settings["dataset"]

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(16)

        left_card = Card("数据集与转换配置")
        left_grid = QGridLayout()
        left_grid.setHorizontalSpacing(12)
        left_grid.setVerticalSpacing(10)
        self.images_box, self.images_edit = self.path_field(
            "图片目录",
            paths["images_dir"],
            self.choose_dir,
            "选择待转换的图片目录",
        )
        self.annotations_box, self.annotations_edit = self.path_field(
            "Labelme 标注目录",
            paths["annotations_dir"],
            self.choose_dir,
            "选择 Labelme 标注目录",
        )
        self.yolo_labels_box, self.yolo_labels_edit = self.path_field(
            "YOLO 标注目录",
            paths["labels_dir"],
            self.choose_dir,
            "选择已有 YOLO 标注目录",
        )
        self.output_box, self.output_edit = self.path_field(
            "输出目录",
            paths["dataset_dir"],
            self.choose_dir,
            "选择数据集输出目录",
        )
        left_grid.addWidget(self.images_box, 0, 0)
        left_grid.addWidget(self.annotations_box, 0, 1)
        left_grid.addWidget(self.yolo_labels_box, 1, 0)
        left_grid.addWidget(self.output_box, 1, 1)
        left_card.layout.addLayout(left_grid)
        controls_row = QHBoxLayout()
        controls_row.setContentsMargins(0, 0, 0, 0)
        controls_row.setSpacing(12)
        labelme_box, self.labelme_check = self.checkbox_with_help(
            "Labelme 转 YOLO",
            app.settings.get("conversion", {}).get("use_labelme", True),
            help_text="开启时自动识别 Labelme 类别并转换为 YOLO；关闭时只对已有 YOLO txt 标注重新分组。",
        )
        self.labelme_check.stateChanged.connect(self.refresh_mode_state)
        controls_row.addWidget(labelme_box)
        controls_row.addStretch(1)
        backup_box, self.backup_yolo_check = self.checkbox_with_help(
            "备份标注文件",
            app.settings.get("conversion", {}).get("backup_yolo_files", False),
            help_text="开启后会把本次转换生成的 YOLO 标注文件和 data.yaml 备份到 data/old 下独立文件夹中，支持多次备份共存。",
        )
        controls_row.addWidget(backup_box)
        controls_row.addStretch(1)
        self.class_mapping_btn = QPushButton("自定义类别名称")
        self.class_mapping_btn.setObjectName("softButton")
        self.class_mapping_btn.setFixedWidth(130)
        self.class_mapping_btn.clicked.connect(self.open_class_mapping_dialog)
        controls_row.addWidget(self.class_mapping_btn)
        left_card.layout.addLayout(controls_row)

        right_card = Card("转换参数")
        param_grid = QGridLayout()
        param_grid.setHorizontalSpacing(12)
        param_grid.setVerticalSpacing(10)
        self.task_box, self.task_combo = self.hint_combo_field(
            "任务类型",
            app.settings["task"]["mode"],
            ["detect", "obb"],
            "OBB 输出旋转框标签；detect 输出普通矩形框标签。",
        )
        ratios = dataset["split_ratios"]
        self.train_ratio_box, self.train_ratio_edit = self.hint_field(
            "训练",
            str(ratios["train"]),
            "训练集比例，三项合计必须为 1.0。",
            placeholder="0.0 - 1.0",
        )
        self.val_ratio_box, self.val_ratio_edit = self.hint_field(
            "验证",
            str(ratios["val"]),
            "验证集比例，用于训练中评估模型。",
            placeholder="0.0 - 1.0",
        )
        self.test_ratio_box, self.test_ratio_edit = self.hint_field(
            "测试",
            str(ratios["test"]),
            "测试集比例，用于最终检测泛化效果。",
            placeholder="0.0 - 1.0",
        )
        self.seed_box, self.seed_edit = self.hint_field(
            "随机种子",
            str(dataset["random_seed"]),
            "控制随机划分的可复现性；同一数据和种子会得到相同划分。",
            placeholder="例如 42",
        )
        line_box = QWidget()
        line_layout = QVBoxLayout(line_box)
        line_layout.setContentsMargins(0, 0, 0, 0)
        line_layout.setSpacing(4)
        self.line_caption, self.line_label, _line_icon = self._caption_widget(
            "直线拓展宽度",
            help_text="仅在 OBB + Labelme line 标注时生效，按该半宽把直线扩展成旋转矩形。",
            object_name="fieldLabel",
        )
        self.line_edit = QLineEdit(str(dataset["line_to_obb"]["half_width"]))
        self.line_edit.setPlaceholderText("仅 OBB + Labelme line")
        line_layout.addWidget(self.line_caption)
        line_layout.addWidget(self.line_edit)
        param_grid.addWidget(self.task_box, 0, 0)
        param_grid.addWidget(self.train_ratio_box, 0, 1)
        param_grid.addWidget(self.val_ratio_box, 1, 0)
        param_grid.addWidget(self.test_ratio_box, 1, 1)
        param_grid.addWidget(self.seed_box, 2, 0)
        param_grid.addWidget(line_box, 2, 1)
        right_card.layout.addLayout(param_grid)

        top_row.addWidget(left_card, 3)
        top_row.addWidget(right_card, 2)
        layout.addLayout(top_row)

        actions = QHBoxLayout()
        preview_button = QPushButton("预览转换")
        preview_button.clicked.connect(self.preview)
        run_button = QPushButton("执行转换")
        run_button.clicked.connect(self.run)
        actions.addWidget(preview_button)
        actions.addWidget(run_button)
        actions.addStretch(1)
        layout.addLayout(actions)
        self.log = QTextEdit()
        self.prepare_readonly_text(self.log)
        self.log.setPlaceholderText(
            "预览或执行后将在这里显示数据集划分、类别统计、跳过标签与输出路径。"
        )
        layout.addWidget(self.log, 1)
        self._connect_persistence()
        self.task_combo.currentTextChanged.connect(self.refresh_mode_state)
        self.refresh_mode_state()

    def _section_card(self, title: str, content_layout):
        card = Card(title)
        card.layout.addLayout(content_layout)
        return card

    def hint_field(
        self, label: str, value: str, tooltip: str, placeholder: str = ""
    ):
        return self.field(
            label, value, placeholder=placeholder, help_text=tooltip
        )

    def hint_combo_field(
        self, label: str, value: str, values: list[str], tooltip: str
    ):
        return self.combo_field(label, value, values, help_text=tooltip)

    def refresh_mode_state(self):
        labelme_enabled = self.labelme_check.isChecked()
        enabled = labelme_enabled and self.task_combo.currentText() == "obb"
        for widget in (self.line_caption, self.line_edit):
            widget.setEnabled(enabled)
        self.class_mapping_btn.setEnabled(labelme_enabled)
        self.backup_yolo_check.setEnabled(labelme_enabled)

    def _connect_persistence(self):
        self.images_edit.textChanged.connect(
            lambda _text: self.update_setting(
                "paths", "images_dir", value=self.resolve_path_text(self.images_edit)
            )
        )
        self.annotations_edit.textChanged.connect(
            lambda _text: self.update_setting(
                "paths",
                "annotations_dir",
                value=self.resolve_path_text(self.annotations_edit),
            )
        )
        self.yolo_labels_edit.textChanged.connect(
            lambda _text: self.update_setting(
                "paths",
                "labels_dir",
                value=self.resolve_path_text(self.yolo_labels_edit),
            )
        )
        self.output_edit.textChanged.connect(
            lambda _text: self.update_setting(
                "paths", "dataset_dir", value=self.resolve_path_text(self.output_edit)
            )
        )
        self.labelme_check.toggled.connect(
            lambda checked: self.update_setting(
                "conversion", "use_labelme", value=bool(checked)
            )
        )
        self.backup_yolo_check.toggled.connect(
            lambda checked: self.update_setting(
                "conversion", "backup_yolo_files", value=bool(checked)
            )
        )
        self.task_combo.currentTextChanged.connect(
            lambda value: self.update_setting("task", "mode", value=value)
        )
        self.train_ratio_edit.textChanged.connect(
            lambda text: self._persist_ratio("train", text)
        )
        self.val_ratio_edit.textChanged.connect(
            lambda text: self._persist_ratio("val", text)
        )
        self.test_ratio_edit.textChanged.connect(
            lambda text: self._persist_ratio("test", text)
        )
        self.seed_edit.textChanged.connect(self._persist_seed)
        self.line_edit.textChanged.connect(self._persist_line_width)

    def _persist_ratio(self, key: str, text: str):
        try:
            value = float(text)
        except ValueError:
            return
        self.app.settings.setdefault("dataset", {}).setdefault("split_ratios", {})[
            key
        ] = value
        self.save_settings()

    def _persist_seed(self, text: str):
        try:
            value = int(text)
        except ValueError:
            return
        self.app.settings.setdefault("dataset", {})["random_seed"] = value
        self.save_settings()

    def _persist_line_width(self, text: str):
        try:
            value = float(text)
        except ValueError:
            return
        self.app.settings.setdefault("dataset", {}).setdefault("line_to_obb", {})[
            "half_width"
        ] = value
        self.save_settings()

    def ratios(self) -> tuple[float, float, float]:
        return (
            float(self.train_ratio_edit.text().strip()),
            float(self.val_ratio_edit.text().strip()),
            float(self.test_ratio_edit.text().strip()),
        )

    def config(self):
        train, val, test = self.ratios()
        return ConversionConfig(
            task_mode=self.task_combo.currentText(),
            images_dir=self.path_from_edit(self.images_edit),
            annotations_dir=self.path_from_edit(
                self.annotations_edit
                if self.labelme_check.isChecked()
                else self.yolo_labels_edit
            ),
            output_dir=self.path_from_edit(self.output_edit),
            labels_dir=Path(self.app.settings["paths"]["labels_dir"]),
            class_names=[],
            source_format="labelme" if self.labelme_check.isChecked() else "yolo",
            train_ratio=train,
            val_ratio=val,
            test_ratio=test,
            random_seed=int(self.seed_edit.text()),
            line_to_obb=self.labelme_check.isChecked()
            and self.task_combo.currentText() == "obb",
            line_half_width=float(self.line_edit.text()),
            backup_yolo_files=self.backup_yolo_check.isChecked(),
            class_name_mapping=dict(
                self.app.settings.get("conversion", {}).get("class_name_mappings", {})
            ),
        )

    def open_class_mapping_dialog(self):
        annotation_dir = self.path_from_edit(self.annotations_edit)
        detected_names = detect_labelme_classes(annotation_dir)
        if not detected_names:
            QMessageBox.warning(
                self,
                "未检测到类别",
                "当前 Labelme 标注目录中没有识别到有效类别，请先确认目录和标注文件。",
            )
            return
        dialog = ClassMappingDialog(
            detected_names,
            self.app.settings.get("conversion", {}).get("class_name_mappings", {}),
            self,
        )
        if dialog.exec():
            self.update_setting(
                "conversion", "class_name_mappings", value=dialog.get_mapping()
            )

    def preview(self):
        try:
            config = self.config()
            result = preview_conversion(config)
            self.log.setPlainText(
                format_conversion_result(result, config, preview=True)
            )
        except Exception as exc:
            self.log.setPlainText(str(exc))

    def run(self):
        try:
            config = self.config()
            result = run_conversion(config)
            self.log.setPlainText(format_conversion_result(result, config))
        except Exception:
            self.log.setPlainText(traceback.format_exc())
