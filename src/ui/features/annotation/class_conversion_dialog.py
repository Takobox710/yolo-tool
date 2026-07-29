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


class ClassConversionDialog(QDialog):
    def __init__(self, class_names: list[str], annotation_counts: list[int], parent=None):
        super().__init__(parent)
        self.setWindowTitle("转换类别")
        self.resize(360, 180)
        self.class_names = list(class_names)
        self.annotation_counts = list(annotation_counts)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("选择要转换的源类别和目标类别"))
        row = QHBoxLayout()
        self.source_combo = QComboBox()
        self.source_combo.addItems(self.class_names)
        row.addWidget(self.source_combo, 1)
        row.addWidget(QLabel("转换为"))
        self.target_combo = QComboBox()
        self.target_combo.addItems(self.class_names)
        if len(self.class_names) > 1:
            self.target_combo.setCurrentIndex(1)
        row.addWidget(self.target_combo, 1)
        layout.addLayout(row)
        self.count_label = QLabel()
        layout.addWidget(self.count_label)
        self.source_combo.currentIndexChanged.connect(self._refresh_count)
        self._refresh_count(self.source_combo.currentIndex())
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("确定")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self._accept_conversion)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _refresh_count(self, source: int) -> None:
        count = self.annotation_counts[source] if 0 <= source < len(self.annotation_counts) else 0
        self.count_label.setText(f"当前源类别包含 {count} 个标注。")

    def _accept_conversion(self) -> None:
        source = self.source_combo.currentIndex()
        target = self.target_combo.currentIndex()
        if source == target:
            QMessageBox.information(self, "转换类别", "源类别和目标类别不能相同。")
            return
        count = self.annotation_counts[source] if 0 <= source < len(self.annotation_counts) else 0
        if not count:
            QMessageBox.information(self, "转换类别", "源类别当前没有标注。")
            return
        self.accept()

    def values(self) -> tuple[int, int]:
        return self.source_combo.currentIndex(), self.target_combo.currentIndex()




