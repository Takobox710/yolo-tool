from __future__ import annotations

from src.services.model_export import resolve_export_format
from src.services.runtime import invalidate_cache
from src.services.runtime.variant import CPU_VARIANT, installed_variant


_FORMAT_OPTION_KEYS = (
    "simplify",
    "dynamic_batch",
    "dynamic_height",
    "dynamic_width",
    "nms",
    "agnostic_nms",
    "opset",
    "workspace",
    "optimize",
    "calibration_data",
    "calibration_samples",
    "validate_quantized",
    "validation_samples",
)


class ModelExportStateMixin:
    def model_export_package_installing_changed(self, installing: bool) -> None:
        self.install_btn.setEnabled(not installing and not self.is_exporting)
        self.install_btn.setVisible(installed_variant() != CPU_VARIANT)
        self.install_status.setVisible(installing)
        if installing:
            self.install_status.setText("正在准备安装")
        else:
            self.install_status.clear()
            self.update_option_visibility()

    def model_export_package_install_progress(self, message: str, value: int) -> None:
        self.install_status.setText(f"{message} {value}%")

    def model_export_package_installed(self, _installed) -> None:
        invalidate_cache("dependency_versions")
        self.update_option_visibility()

    def _format_options_for(self, export_format: str) -> dict:
        cached = self._format_option_cache.get(export_format)
        if cached is not None:
            return dict(cached)
        return self._capture_format_options(export_format)

    def _capture_format_options(self, export_format: str) -> dict:
        is_onnx = export_format == "onnx"
        values = {
            "simplify": self.simplify_check.isChecked(),
            "dynamic_batch": (
                self.onnx_dynamic_batch_check.isChecked()
                if is_onnx
                else self.dynamic_input_check.isChecked()
                if self._uses_unified_dynamic_input(export_format)
                else self.dynamic_batch_check.isChecked()
            ),
            "dynamic_height": (
                self.onnx_dynamic_size_check.isChecked()
                if is_onnx
                else self.dynamic_height_check.isChecked()
            ),
            "dynamic_width": (
                self.onnx_dynamic_size_check.isChecked()
                if is_onnx
                else self.dynamic_width_check.isChecked()
            ),
            "nms": self.nms_check.isChecked(),
            "agnostic_nms": self.agnostic_nms_check.isChecked(),
            "opset": self.opset_spin.value() or None,
            "workspace": self.workspace_spin.value(),
            "optimize": self.optimize_check.isChecked(),
            "calibration_data": self.resolve_path_text(self.calibration_data_edit),
            "calibration_samples": self.calibration_samples_spin.value(),
            "validate_quantized": self.validate_quantized_check.isChecked(),
            "validation_samples": self.validation_samples_spin.value(),
        }
        return {key: values[key] for key in _FORMAT_OPTION_KEYS}

    def _restore_format_options(self, export_format: str) -> None:
        values = self._format_option_cache.setdefault(
            export_format, self._capture_format_options(export_format)
        )
        self._format_switching = True
        try:
            self._set_checked(self.simplify_check, values["simplify"])
            self._set_checked(self.nms_check, values["nms"])
            self._set_checked(self.agnostic_nms_check, values["agnostic_nms"])
            self._set_value(self.opset_spin, values["opset"] or 0)
            self._set_value(self.workspace_spin, values["workspace"] or 0.0)
            self._set_checked(self.optimize_check, values["optimize"])
            self._set_checked(
                self.dynamic_input_check,
                values["dynamic_batch"] if self._uses_unified_dynamic_input(export_format) else False,
            )
            self._set_checked(self.dynamic_batch_check, values["dynamic_batch"])
            self._set_checked(self.dynamic_height_check, values["dynamic_height"])
            self._set_checked(self.dynamic_width_check, values["dynamic_width"])
            self._set_checked(self.onnx_dynamic_batch_check, values["dynamic_batch"])
            self._set_checked(self.onnx_dynamic_size_check, values["dynamic_height"] or values["dynamic_width"])
            self.calibration_data_edit.setText(
                self.display_path(values["calibration_data"])
                if values["calibration_data"]
                else ""
            )
            self._set_value(self.calibration_samples_spin, values["calibration_samples"])
            self._set_checked(self.validate_quantized_check, values["validate_quantized"])
            self._set_value(self.validation_samples_spin, values["validation_samples"])
        finally:
            self._format_switching = False

    def _persist_config(self, config):
        self._format_option_cache[config.export_format] = self._capture_format_options(
            config.export_format
        )
        settings = {
            "model_path": str(config.model_path),
            "output_dir": self.resolve_path_text(self.output_edit),
            "format": config.export_format,
            "imgsz": config.imgsz,
            "simplify": config.simplify,
            "precision": config.precision,
            "batch": config.batch,
            "dynamic_batch": config.dynamic_batch,
            "dynamic_height": config.dynamic_height,
            "dynamic_width": config.dynamic_width,
            "nms": config.nms,
            "nms_conf": config.nms_conf,
            "nms_iou": config.nms_iou,
            "nms_max_det": config.nms_max_det,
            "agnostic_nms": config.agnostic_nms,
            "opset": config.opset,
            "workspace": config.workspace,
            "optimize": config.optimize,
            "calibration_data": self.resolve_path_text(self.calibration_data_edit),
            "calibration_samples": config.calibration_samples,
            "validate_quantized": config.validate_quantized,
            "validation_samples": config.validation_samples,
        }
        for key, value in settings.items():
            self.update_setting("model_export", key, value=value)

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
        self.format_combo.currentTextChanged.connect(self._persist_format)
        self.precision_combo.currentTextChanged.connect(self._persist_precision)
        self.imgsz_edit.textChanged.connect(self._persist_imgsz)
        self.batch_spin.valueChanged.connect(
            lambda value: self.update_setting("model_export", "batch", value=int(value))
        )
        self.conf_spin.valueChanged.connect(
            lambda value: self.update_setting("model_export", "nms_conf", value=float(value))
        )
        self.iou_spin.valueChanged.connect(
            lambda value: self.update_setting("model_export", "nms_iou", value=float(value))
        )
        self.max_det_spin.valueChanged.connect(
            lambda value: self.update_setting("model_export", "nms_max_det", value=int(value))
        )

        for control, key in (
            (self.simplify_check, "simplify"),
            (self.nms_check, "nms"),
            (self.agnostic_nms_check, "agnostic_nms"),
            (self.optimize_check, "optimize"),
            (self.validate_quantized_check, "validate_quantized"),
        ):
            control.toggled.connect(
                lambda checked, setting=key: self._persist_option(setting, bool(checked))
            )
        self.dynamic_input_check.toggled.connect(self._persist_dynamic_input)
        self.dynamic_batch_check.toggled.connect(
            lambda checked: self._persist_option("dynamic_batch", bool(checked))
        )
        self.dynamic_height_check.toggled.connect(
            lambda checked: self._persist_option("dynamic_height", bool(checked))
        )
        self.dynamic_width_check.toggled.connect(
            lambda checked: self._persist_option("dynamic_width", bool(checked))
        )
        self.onnx_dynamic_batch_check.toggled.connect(
            lambda checked: self._persist_option("dynamic_batch", bool(checked))
        )
        self.onnx_dynamic_size_check.toggled.connect(self._persist_onnx_dynamic_size)
        self.opset_spin.valueChanged.connect(self._persist_opset)
        self.workspace_spin.valueChanged.connect(
            lambda value: self._persist_option("workspace", float(value))
        )
        self.calibration_data_edit.textChanged.connect(
            lambda _text: self._persist_option(
                "calibration_data", self.resolve_path_text(self.calibration_data_edit)
            )
        )
        self.calibration_samples_spin.valueChanged.connect(
            lambda value: self._persist_option("calibration_samples", int(value))
        )
        self.validation_samples_spin.valueChanged.connect(
            lambda value: self._persist_option("validation_samples", int(value))
        )

    def _persist_format(self, text: str):
        if getattr(self, "_format_switching", False):
            return
        previous = getattr(self, "_active_format_argument", None)
        if previous:
            self._format_option_cache[previous] = self._capture_format_options(previous)
        new_format = resolve_export_format(text).argument
        self._active_format_argument = new_format
        self.update_setting("model_export", "format", value=new_format)
        self._restore_format_options(new_format)
        self._persist_current_format_options()
        self.update_option_visibility()

    def _persist_precision(self, text: str):
        value = {"FP16": "fp16", "INT8": "int8"}.get(text, "fp32")
        self.update_setting("model_export", "precision", value=value)
        self.update_option_visibility()

    def _persist_imgsz(self, text: str):
        try:
            value = int(text)
        except ValueError:
            return
        self.update_setting("model_export", "imgsz", value=value)

    def _persist_opset(self, value: int):
        self._persist_option("opset", int(value) or None)

    def _persist_dynamic_input(self, checked: bool):
        checked = bool(checked)
        self._set_checked(self.dynamic_batch_check, checked)
        self._set_checked(self.dynamic_height_check, checked)
        self._set_checked(self.dynamic_width_check, checked)
        for key in ("dynamic_batch", "dynamic_height", "dynamic_width"):
            self._persist_option(key, checked)

    def _persist_onnx_dynamic_size(self, checked: bool):
        checked = bool(checked)
        self._persist_option("dynamic_height", checked)
        self._persist_option("dynamic_width", checked)
        self._set_checked(self.dynamic_height_check, checked)
        self._set_checked(self.dynamic_width_check, checked)

    def _persist_option(self, key: str, value) -> None:
        if getattr(self, "_format_switching", False):
            return
        self.update_setting("model_export", key, value=value)
        active = getattr(self, "_active_format_argument", None)
        if active:
            self._format_option_cache[active] = self._capture_format_options(active)

    def _persist_current_format_options(self) -> None:
        active = getattr(self, "_active_format_argument", None)
        if not active:
            return
        values = self._format_option_cache.get(active)
        if values is None:
            return
        for key, value in values.items():
            self.update_setting("model_export", key, value=value)

    @staticmethod
    def _uses_unified_dynamic_input(export_format: str) -> bool:
        return export_format != "onnx"

    @staticmethod
    def _set_checked(control, value: bool) -> None:
        control.blockSignals(True)
        control.setChecked(bool(value))
        control.blockSignals(False)

    @staticmethod
    def _set_value(control, value) -> None:
        control.blockSignals(True)
        control.setValue(value)
        control.blockSignals(False)


__all__ = ["ModelExportStateMixin"]
