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
        self.selected_shape = "rect"
        self.sam_models = list(sam_models or [])
        self.sam_enabled = bool(sam_enabled)
        self.sam_toggle_callback = sam_toggle_callback
        self.sam_model_callback = sam_model_callback
        self.sam_settings = dict(sam_settings or {})
        self.sam_settings_callback = sam_settings_callback
        self.setWindowTitle("选择标注类型")
        self.resize(240, 424 if line_expand_enabled else 380)
        from src.ui.features.annotation.draw_shape_layout import build_dialog_ui

        build_dialog_ui(self, line_expand_enabled, selected_sam_model)

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



