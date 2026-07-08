from __future__ import annotations

import shlex

from src.services.conversion import (
    ClassMappingRow,
    build_class_mapping_rows,
    parse_class_mapping_rows,
)
from src.shared.qt import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QModelIndex,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    Qt,
    QVBoxLayout,
)


class _PlainEditTable(QTableWidget):
    def mousePressEvent(self, event):  # noqa: N802 - Qt API name
        if not self.indexAt(event.position().toPoint()).isValid():
            self.clearSelection()
            self.setCurrentIndex(QModelIndex())
            self.clearFocus()
        super().mousePressEvent(event)
        if not self.indexAt(event.position().toPoint()).isValid():
            self.clearSelection()
            self.setCurrentIndex(QModelIndex())


class CommandDialog(QDialog):
    def __init__(self, command: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("编辑训练命令")
        self.resize(700, 200)
        self.setMinimumSize(350, 100)
        layout = QVBoxLayout(self)
        self.command_edit = QPlainTextEdit(" ".join(command))
        layout.addWidget(self.command_edit)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_command(self) -> list[str]:
        text = self.command_edit.toPlainText().strip()
        if not text:
            return []
        try:
            return shlex.split(text, posix=False)
        except ValueError:
            return text.split()


class ClassMappingDialog(QDialog):
    def __init__(
        self,
        detected_labelme_names: list[str],
        stored_mapping: dict[str, str] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._detected_labelme_names = [
            str(name).strip() for name in detected_labelme_names if str(name).strip()
        ]
        self.setWindowTitle("自定义类别名称")
        self.resize(560, 360)
        self.setMinimumSize(430, 300)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        tools = QHBoxLayout()
        tools.setContentsMargins(0, 0, 0, 0)
        hint = QLabel(f"已识别 {len(self._detected_labelme_names)} 个 Labelme 类别")
        hint.setToolTip(
            "左侧填写 YOLO 类别名称，右侧填写 Labelme 类别名称。多个 Labelme 类别可用英文逗号分隔映射到同一个 YOLO 类别。"
        )
        tools.addWidget(hint)
        tools.addStretch(1)
        self.add_btn = QPushButton("新增一行")
        self.add_btn.clicked.connect(lambda: self._append_row(ClassMappingRow("", "")))
        tools.addWidget(self.add_btn)
        self.remove_btn = QPushButton("删除选中")
        self.remove_btn.clicked.connect(self._remove_selected_rows)
        tools.addWidget(self.remove_btn)
        layout.addLayout(tools)

        self.table = _PlainEditTable(0, 2)
        self.table.setHorizontalHeaderLabels(["YOLO 类别名称", "Labelme 类别名称"])
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.setAlternatingRowColors(False)
        self.table.setShowGrid(True)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectItems
        )
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.CurrentChanged
            | QAbstractItemView.EditTrigger.SelectedClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
            | QAbstractItemView.EditTrigger.AnyKeyPressed
        )
        self.table.setStyleSheet(
            """
            QTableWidget {
                background: palette(base);
                alternate-background-color: palette(base);
                color: palette(text);
                border: 1px solid palette(mid);
                gridline-color: palette(mid);
                selection-background-color: #DCEEFF;
                selection-color: palette(text);
            }
            QTableWidget::item {
                padding: 4px;
                border: none;
            }
            QTableWidget::item:selected {
                background: #DCEEFF;
                color: palette(text);
            }
            QTableWidget QLineEdit {
                background: palette(base);
                color: palette(text);
                border: 1px solid palette(mid);
                border-radius: 0px;
                padding: 0px 2px;
                margin: 0px;
            }
            QHeaderView::section {
                background: palette(button);
                color: palette(button-text);
                border: 1px solid palette(mid);
                padding: 4px 6px;
                font-weight: normal;
            }
            """
        )
        layout.addWidget(self.table, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        for row in build_class_mapping_rows(self._detected_labelme_names, stored_mapping):
            self._append_row(row)
        if self.table.rowCount() == 0:
            for name in self._detected_labelme_names:
                self._append_row(ClassMappingRow(name, name))

    def _append_row(self, row: ClassMappingRow) -> None:
        current = self.table.rowCount()
        self.table.insertRow(current)
        yolo_item = QTableWidgetItem(row.yolo_name)
        yolo_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        labelme_item = QTableWidgetItem(row.labelme_names)
        labelme_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(current, 0, yolo_item)
        self.table.setItem(current, 1, labelme_item)

    def _remove_selected_rows(self) -> None:
        rows = sorted({item.row() for item in self.table.selectedItems()}, reverse=True)
        for row in rows:
            self.table.removeRow(row)

    def _rows(self) -> list[ClassMappingRow]:
        rows: list[ClassMappingRow] = []
        for index in range(self.table.rowCount()):
            yolo_item = self.table.item(index, 0)
            labelme_item = self.table.item(index, 1)
            rows.append(
                ClassMappingRow(
                    yolo_name=yolo_item.text() if yolo_item else "",
                    labelme_names=labelme_item.text() if labelme_item else "",
                )
            )
        return rows

    def _accept_if_valid(self) -> None:
        mapping, errors = parse_class_mapping_rows(
            self._rows(), self._detected_labelme_names
        )
        if errors:
            QMessageBox.warning(self, "类别映射无效", "\n".join(errors))
            return
        self._mapping = mapping
        self.accept()

    def get_mapping(self) -> dict[str, str]:
        return getattr(self, "_mapping", {})


