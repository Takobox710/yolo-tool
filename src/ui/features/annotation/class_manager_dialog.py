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


from src.ui.features.annotation.class_conversion_dialog import ClassConversionDialog
class ClassManagerDialog(QDialog):
    def __init__(
        self, class_names: list[str], parent=None, *, annotations=None, annotation_counts=None
    ):
        super().__init__(parent)
        self.setWindowTitle("管理类别")
        self.resize(360, 420)
        self.class_names = list(class_names)
        self._original_annotation_class_ids = [
            int(annotation.class_id) for annotation in (annotations or [])
        ]
        self._annotation_class_ids = list(self._original_annotation_class_ids)
        self._annotation_counts = list(annotation_counts or [])
        if not self._annotation_counts:
            self._annotation_counts = [0] * len(self.class_names)
            for class_id in self._annotation_class_ids:
                if 0 <= class_id < len(self._annotation_counts):
                    self._annotation_counts[class_id] += 1
        if len(self._annotation_counts) < len(self.class_names):
            self._annotation_counts.extend(
                [0] * (len(self.class_names) - len(self._annotation_counts))
            )
        self._conversion_operations: list[tuple[str, str]] = []
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
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("确定")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        button_row = QHBoxLayout()
        self.convert_button = QPushButton("转换类别")
        self.convert_button.clicked.connect(self.open_conversion_dialog)
        button_row.addWidget(self.convert_button)
        button_row.addStretch(1)
        button_row.addWidget(buttons)
        layout.addLayout(button_row)
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
        previous_name = self.class_names[row]
        self.class_names[row] = name
        self._conversion_operations = [
            (
                name if source_name == previous_name else source_name,
                name if target_name == previous_name else target_name,
            )
            for source_name, target_name in self._conversion_operations
        ]
        self.refresh()
        self.listing.setCurrentRow(row)

    def delete_class(self) -> None:
        row = self.listing.currentRow()
        if row < 0:
            return
        dependent_count = self._annotation_counts[row]
        if dependent_count:
            QMessageBox.warning(
                self,
                "管理类别",
                f"你有 {dependent_count} 个标注依赖此类别名，无法删除。",
            )
            return
        if len(self.class_names) <= 1:
            QMessageBox.information(self, "管理类别", "至少保留一个类别。")
            return
        del self.class_names[row]
        self._annotation_class_ids = [
            class_id - 1 if class_id > row else class_id
            for class_id in self._annotation_class_ids
        ]
        del self._annotation_counts[row]
        self.refresh()

    def open_conversion_dialog(self) -> None:
        dialog = ClassConversionDialog(
            self.class_names, self._annotation_counts, self
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        source, target = dialog.values()
        self.convert_classes(source, target)

    def convert_classes(self, source: int, target: int) -> None:
        if source < 0 or target < 0:
            return
        if source == target:
            QMessageBox.information(self, "转换类别", "源类别和目标类别不能相同。")
            return
        count = self._annotation_counts[source]
        if not count:
            QMessageBox.information(self, "转换类别", "源类别当前没有标注。")
            return
        self._annotation_class_ids = [
            target if class_id == source else class_id
            for class_id in self._annotation_class_ids
        ]
        self._annotation_counts[target] += count
        self._annotation_counts[source] = 0
        self._conversion_operations.append(
            (self.class_names[source], self.class_names[target])
        )

    @property
    def annotation_class_ids(self) -> list[int]:
        return list(self._annotation_class_ids)

    @property
    def annotation_class_ids_changed(self) -> bool:
        return self._annotation_class_ids != self._original_annotation_class_ids

    @property
    def conversion_operations(self) -> list[tuple[str, str]]:
        return list(self._conversion_operations)




