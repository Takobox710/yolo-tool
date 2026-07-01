from __future__ import annotations

import traceback
from pathlib import Path

from scr.services.conversion_service import ConversionConfig, format_conversion_result, preview_conversion, run_conversion
from scr.ui.page_base import BasePage, Card
from scr.ui.qt import QCheckBox, QComboBox, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QVBoxLayout, QWidget

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
            "图片目录", paths["images_dir"], self.choose_dir
        )
        self.annotations_box, self.annotations_edit = self.path_field(
            "Labelme 标注目录", paths["annotations_dir"], self.choose_dir
        )
        self.yolo_labels_box, self.yolo_labels_edit = self.path_field(
            "YOLO 标注目录", paths["labels_dir"], self.choose_dir
        )
        self.output_box, self.output_edit = self.path_field(
            "输出目录", paths["dataset_dir"], self.choose_dir
        )
        left_grid.addWidget(self.images_box, 0, 0)
        left_grid.addWidget(self.annotations_box, 0, 1)
        left_grid.addWidget(self.yolo_labels_box, 1, 0)
        left_grid.addWidget(self.output_box, 1, 1)
        left_card.layout.addLayout(left_grid)
        self.labelme_check = QCheckBox("Labelme 转 YOLO (?)")
        self.labelme_check.setToolTip(
            "开启时自动识别 Labelme 类别并转换为 YOLO；关闭时只对已有 YOLO txt 标注重新分组。"
        )
        self.labelme_check.setChecked(True)
        self.labelme_check.stateChanged.connect(self.refresh_mode_state)
        left_card.layout.addWidget(self.labelme_check)

        right_card = Card("转换参数")
        param_grid = QGridLayout()
        param_grid.setHorizontalSpacing(12)
        param_grid.setVerticalSpacing(10)
        self.task_box, self.task_combo = self.hint_combo_field(
            "任务类型",
            app.settings["task"]["mode"],
            ["obb", "detect"],
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
        )
        line_box = QWidget()
        line_layout = QVBoxLayout(line_box)
        line_layout.setContentsMargins(0, 0, 0, 0)
        line_layout.setSpacing(4)
        self.line_label = self.hint_label(
            "直线拓展宽度",
            "仅在 OBB + Labelme line 标注时生效，按该半宽把直线扩展成旋转矩形。",
        )
        self.line_label.setObjectName("fieldLabel")
        self.line_edit = QLineEdit(str(dataset["line_to_obb"]["half_width"]))
        self.line_edit.setPlaceholderText("仅 OBB + Labelme line")
        line_layout.addWidget(self.line_label)
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
        self.log.setReadOnly(True)
        self.log.setPlaceholderText(
            "预览或执行后将在这里显示数据集划分、类别统计、跳过标签与输出路径。"
        )
        layout.addWidget(self.log, 1)
        self.task_combo.currentTextChanged.connect(self.refresh_mode_state)
        self.refresh_mode_state()

    def _section_card(self, title: str, content_layout):
        card = Card(title)
        card.layout.addLayout(content_layout)
        return card

    def hint_label(self, text: str, tooltip: str):
        label = QLabel(f"{text} (?)")
        label.setToolTip(tooltip)
        return label

    def hint_field(
        self, label: str, value: str, tooltip: str, placeholder: str = ""
    ):
        box = QWidget()
        field_layout = QVBoxLayout(box)
        field_layout.setContentsMargins(0, 0, 0, 0)
        field_layout.setSpacing(4)
        caption = self.hint_label(label, tooltip)
        caption.setObjectName("fieldLabel")
        edit = QLineEdit(str(value))
        if placeholder:
            edit.setPlaceholderText(placeholder)
        field_layout.addWidget(caption)
        field_layout.addWidget(edit)
        return box, edit

    def hint_combo_field(
        self, label: str, value: str, values: list[str], tooltip: str
    ):
        box = QWidget()
        field_layout = QVBoxLayout(box)
        field_layout.setContentsMargins(0, 0, 0, 0)
        field_layout.setSpacing(4)
        caption = self.hint_label(label, tooltip)
        caption.setObjectName("fieldLabel")
        combo = QComboBox()
        combo.addItems(values)
        if value in values:
            combo.setCurrentText(value)
        field_layout.addWidget(caption)
        field_layout.addWidget(combo)
        return box, combo

    def refresh_mode_state(self):
        labelme_enabled = self.labelme_check.isChecked()
        self.annotations_box.setEnabled(labelme_enabled)
        self.yolo_labels_box.setEnabled(not labelme_enabled)
        enabled = labelme_enabled and self.task_combo.currentText() == "obb"
        for widget in (self.line_label, self.line_edit):
            widget.setEnabled(enabled)

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
            line_to_obb=self.labelme_check.isChecked()
            and self.task_combo.currentText() == "obb",
            line_half_width=float(self.line_edit.text()),
        )

    def preview(self):
        try:
            config = self.config()
            result = preview_conversion(config)
            preview_result = type(
                "PreviewReport",
                (),
                {
                    "labeled_train_count": result.planned_splits.get("train", 0),
                    "labeled_val_count": result.planned_splits.get("val", 0),
                    "labeled_test_count": result.planned_splits.get("test", 0),
                    "total_boxes": 0,
                    "unlabeled_count": result.unlabeled_count,
                    "yaml_path": result.output_dir / "data.yaml",
                    "labels_dir": result.labels_dir,
                    "missing_labels": {},
                    "stats": {"train": {}, "val": {}, "test": {}},
                    "class_names": [],
                },
            )()
            self.log.setPlainText(
                format_conversion_result(preview_result, config, preview=True)
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
