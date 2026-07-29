from __future__ import annotations

import traceback
from pathlib import Path

from src.services.conversion import (
    ConversionConfig,
    format_conversion_result,
    preview_conversion,
    run_conversion,
)
from src.ui.shared.dialogs import ClassMappingDialog
from src.ui.shared.page_base import BasePage
from src.shared.qt import QMessageBox
from src.ui.features.data.convert.layout import (
    LABELME_MODE,
    YOLO_MODE,
    build_convert_layout,
)


class ConvertTab(BasePage):
    def __init__(self, context):
        super().__init__(context)
        build_convert_layout(self)
        self._connect_persistence()
        self.task_combo.currentTextChanged.connect(self.refresh_mode_state)
        self.refresh_mode_state()

    def on_setting_changed(self, keys, value):
        fields = {
            ("paths", "images_dir"): self.images_edit,
            ("paths", "annotations_dir"): self.annotations_edit,
            ("paths", "labels_dir"): self.yolo_labels_edit,
            ("paths", "dataset_dir"): self.output_edit,
        }
        edit = fields.get(keys)
        if edit is None:
            return
        edit.blockSignals(True)
        edit.setText(self.display_path(value))
        edit.blockSignals(False)
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
        labelme_enabled = self.is_labelme_mode()
        self.class_mapping_btn.setVisible(labelme_enabled)
        self.task_box.setEnabled(labelme_enabled)

    def is_labelme_mode(self) -> bool:
        return self.mode_combo.currentText() == LABELME_MODE

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
        self.mode_combo.currentTextChanged.connect(
            lambda value: self.update_setting(
                "conversion", "use_labelme", value=value == LABELME_MODE
            )
        )
        self.mode_combo.currentTextChanged.connect(self.refresh_mode_state)
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

    def _persist_ratio(self, key: str, text: str):
        try:
            value = float(text)
        except ValueError:
            return
        setattr(self.context.settings.dataset.split_ratios, key, value)
        self.save_settings()

    def ratios(self) -> tuple[float, float, float]:
        return (
            float(self.train_ratio_edit.text().strip()),
            float(self.val_ratio_edit.text().strip()),
            float(self.test_ratio_edit.text().strip()),
        )

    def managed_class_names(self) -> list[str]:
        return [
            str(name).strip()
            for name in self.context.settings.dataset.class_names
            if str(name).strip()
        ]

    def config(self):
        train, val, test = self.ratios()
        return ConversionConfig(
            task_mode=self.task_combo.currentText(),
            images_dir=self.path_from_edit(self.images_edit),
            annotations_dir=self.path_from_edit(
                self.annotations_edit
                if self.is_labelme_mode()
                else self.yolo_labels_edit
            ),
            output_dir=self.path_from_edit(self.output_edit),
            labels_dir=Path(self.context.settings.paths.labels_dir),
            class_names=self.managed_class_names(),
            source_format="labelme" if self.is_labelme_mode() else "yolo",
            train_ratio=train,
            val_ratio=val,
            test_ratio=test,
            random_seed=int(self.context.settings.dataset.random_seed),
            line_to_obb=self.is_labelme_mode()
            and self.task_combo.currentText() in {"obb", "seg"},
            line_half_width=float(self.context.settings.dataset.line_to_obb.half_width),
            backup_yolo_files=self.backup_yolo_check.isChecked(),
            class_name_mapping=dict(
                self.context.settings.conversion.class_name_mappings
            ),
        )

    def open_class_mapping_dialog(self):
        managed_names = self.managed_class_names()
        if not managed_names:
            QMessageBox.warning(
                self,
                "没有管理类别",
                "当前数据标注页的管理类别为空，请先在数据标注页添加类别。",
            )
            return
        dialog = ClassMappingDialog(
            managed_names,
            self.context.settings.conversion.class_name_mappings,
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
