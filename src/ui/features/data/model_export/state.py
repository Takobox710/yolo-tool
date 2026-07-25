from __future__ import annotations

from src.services.model_export import resolve_export_format
from src.services.runtime import invalidate_cache


class ModelExportStateMixin:
    def model_export_package_installing_changed(self, installing: bool) -> None:
        self.install_btn.setEnabled(not installing and not self.is_exporting)
        self.install_btn.setVisible(not installing)
        self.install_controls.setStretch(0, 0 if installing else 1)
        if installing:
            self.install_progress.setValue(0)
            self.install_progress.setFormat("正在准备安装 %p%")
            self.install_progress.setVisible(True)
        else:
            self.install_progress.setVisible(False)
            self.update_environment_status()

    def model_export_package_install_progress(self, message: str, value: int) -> None:
        self.install_progress.setValue(value)
        self.install_progress.setFormat(f"{message} %p%")

    def model_export_package_installed(self, _installed) -> None:
        invalidate_cache("dependency_versions")
        self.update_environment_status()

    def _persist_config(self, config):
        self.update_setting("model_export", "model_path", value=str(config.model_path))
        self.update_setting(
            "model_export",
            "output_dir",
            value=self.resolve_path_text(self.output_edit),
        )
        self.update_setting("model_export", "format", value=config.export_format)
        self.update_setting("model_export", "imgsz", value=config.imgsz)
        self.update_setting("model_export", "simplify", value=config.simplify)

    def _connect_persistence(self):
        self.model_combo.currentTextChanged.connect(
            lambda text: self.update_setting(
                "model_export",
                "model_path",
                value=self.model_path_from_text(text) if text else "",
            )
        )
        self.output_edit.textChanged.connect(
            lambda _text: self.update_setting(
                "model_export",
                "output_dir",
                value=self.resolve_path_text(self.output_edit),
            )
        )
        self.format_combo.currentTextChanged.connect(
            lambda text: self.update_setting(
                "model_export",
                "format",
                value=resolve_export_format(text).argument,
            )
        )
        self.imgsz_edit.textChanged.connect(self._persist_imgsz)
        self.simplify_check.toggled.connect(
            lambda checked: self.update_setting(
                "model_export", "simplify", value=bool(checked)
            )
        )

    def _persist_imgsz(self, text: str):
        try:
            value = int(text)
        except ValueError:
            return
        self.update_setting("model_export", "imgsz", value=value)
