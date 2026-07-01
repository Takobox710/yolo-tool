from __future__ import annotations

from pathlib import Path

from scr.services.rename_service import execute_rename, preview_rename
from scr.ui.helpers import _parse_padding_text
from scr.ui.page_base import BasePage
from scr.ui.qt import Qt, QCheckBox, QGridLayout, QHBoxLayout, QHeaderView, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QTimer, QVBoxLayout

class RenameTab(BasePage):
    def __init__(self, app):
        super().__init__(app)
        self.plan = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        self.folder_box, self.folder_edit = self.path_field(
            "图片文件夹", app.settings["paths"]["images_dir"], self.choose_dir
        )
        self.labelme_box, self.labelme_edit = self.path_field(
            "Labelme 标注文件夹",
            app.settings["paths"]["annotations_dir"],
            self.choose_dir,
        )
        self.yolo_box, self.yolo_edit = self.path_field(
            "YOLO 标注文件夹", app.settings["paths"]["labels_dir"], self.choose_dir
        )
        self.prefix_box, self.prefix_edit = self.field("命名前缀", "A")
        self.start_box, self.start_edit = self.field("起始编号", "1")
        self.padding_box, self.padding_combo = self.combo_field(
            "编号位数", "1", ["1", "2", "3", "4"]
        )
        for index, widget in enumerate(
            [
                self.folder_box,
                self.labelme_box,
                self.yolo_box,
                self.prefix_box,
                self.start_box,
                self.padding_box,
            ]
        ):
            grid.addWidget(widget, index // 3, index % 3)
        self.include_labelme = QCheckBox("Labelme 标注文件一并更改")
        self.include_labelme.setChecked(False)
        self.include_yolo = QCheckBox("YOLO 标注文件一并更改")
        self.include_yolo.setChecked(False)
        grid.addWidget(self.include_labelme, 2, 0)
        grid.addWidget(self.include_yolo, 2, 1)
        layout.addLayout(grid)
        actions = QHBoxLayout()
        run_button = QPushButton("执行重命名")
        run_button.clicked.connect(self.run)
        actions.addWidget(run_button)
        actions.addStretch(1)
        layout.addLayout(actions)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(
            ["图片文件状态", "Labelme 标注状态", "YOLO 标注状态"]
        )
        self.table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.table, 1)
        for edit in [
            self.folder_edit,
            self.labelme_edit,
            self.yolo_edit,
            self.prefix_edit,
            self.start_edit,
        ]:
            edit.textChanged.connect(lambda _text: self.preview())
        self.padding_combo.currentTextChanged.connect(lambda _text: self.preview())
        self.include_labelme.stateChanged.connect(lambda _state: self.preview())
        self.include_yolo.stateChanged.connect(lambda _state: self.preview())
        QTimer.singleShot(100, self.preview)

    def label_status(
        self, source: Path | None, target: Path | None, note: str
    ) -> str:
        if note:
            return note
        if source and target:
            return f"{source.name} -> {target.name}"
        return "不处理"

    def image_status(self, item) -> str:
        if item.conflict:
            return f"目标已存在: {item.new_name}"
        return f"{item.old_name} -> {item.new_name}"

    def preview(self):
        try:
            self.plan = preview_rename(
                self.path_from_edit(self.folder_edit),
                self.prefix_edit.text(),
                int(self.start_edit.text()),
                _parse_padding_text(self.padding_combo.currentText()),
                labelme_dir=self.path_from_edit(self.labelme_edit),
                include_labelme=self.include_labelme.isChecked(),
                labels_dir=self.path_from_edit(self.yolo_edit),
                include_labels=self.include_yolo.isChecked(),
            )
        except Exception:
            return
        self.table.setRowCount(len(self.plan))
        for row, item in enumerate(self.plan):
            image_status = self.image_status(item)
            labelme_status = self.label_status(
                item.labelme_source, item.labelme_target, item.labelme_note
            )
            yolo_status = self.label_status(
                item.label_source, item.label_target, item.note
            )
            values = [image_status, labelme_status, yolo_status]
            for column, value in enumerate(values):
                table_item = QTableWidgetItem(str(value))
                table_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, column, table_item)

    def run(self):
        result = execute_rename(self.plan)
        if result.renamed_count == 0 and result.skipped_count:
            QMessageBox.warning(
                self, "发现冲突", "检测到标注文件目标名称冲突，已取消本次重命名。"
            )
        else:
            QMessageBox.information(
                self,
                "重命名完成",
                f"已重命名图片 {result.renamed_count} 个，Labelme 标注 {result.labelme_renamed_count} 个，YOLO 标注 {result.label_renamed_count} 个。",
            )
        self.preview()
