from __future__ import annotations

from src.services.model_export import capabilities_for, resolve_export_format
from src.shared.qt import QTimer
from src.ui.features.data.model_export import availability as availability_helpers
from src.ui.features.data.model_export.layout import arrange_basic_option_row
from src.ui.features.data.model_export.registry import option_keys_for


class ModelExportVisibilityMixin:
    def update_option_visibility(self, *_args):
        spec = resolve_export_format(self.format_combo.currentText())
        model_kind = self._current_model_kind()
        if model_kind == "sam2" and spec.argument != "onnx":
            self.format_combo.blockSignals(True)
            self.format_combo.setCurrentText("ONNX")
            self.format_combo.blockSignals(False)
            self.update_setting("model_export", "format", value="onnx")
            self._active_format_argument = "onnx"
            spec = resolve_export_format("onnx")
        capabilities = capabilities_for(spec.argument, model_kind)
        is_onnx = spec.argument == "onnx"
        option_keys = set(option_keys_for(spec.argument))
        self._update_format_availability(model_kind)
        self._set_precision_items(capabilities.precisions, spec.argument, model_kind)
        is_sam2 = model_kind == "sam2" and spec.argument == "onnx"
        if is_sam2:
            self._set_line_edit(self.imgsz_edit, "1024")
            self._set_spin_value(self.batch_spin, 1)
        self.imgsz_box.setVisible(True)
        self.batch_box.setVisible(True)
        self.imgsz_edit.setEnabled(not is_sam2 and not self.is_exporting)
        self.batch_spin.setEnabled(
            capabilities.supports_batch and not is_sam2 and not self.is_exporting
        )
        self.conf_spin.setEnabled(capabilities.supports_nms and not self.is_exporting)
        self.iou_spin.setEnabled(capabilities.supports_nms and not self.is_exporting)
        self.max_det_spin.setEnabled(capabilities.supports_nms and not self.is_exporting)

        self.simplify_box.setVisible(
            "simplify" in option_keys and capabilities.supports_simplify
        )
        supports_opset = (
            "opset" in option_keys and capabilities.supports_opset and not is_sam2
        )
        supports_workspace = (
            "workspace" in option_keys and capabilities.supports_workspace
        )
        self.opset_box.setVisible(supports_opset)
        self.workspace_box.setVisible(supports_workspace)
        self.optimize_box.setVisible(
            "optimize" in option_keys and capabilities.supports_optimize
        )
        self.basic_format_box.setVisible(
            capabilities.supports_simplify or capabilities.supports_optimize
        )
        self.basic_format_box.updateGeometry()
        self.inference_format_box.setVisible(supports_opset or supports_workspace)
        has_basic_options = any(
            (
                capabilities.supports_simplify,
                capabilities.supports_optimize,
                "nms" in option_keys and capabilities.supports_nms,
                "dynamic" in option_keys and capabilities.supports_dynamic_batch,
            )
        )
        self.basic_options_box.setVisible(has_basic_options)

        has_dynamic = (
            ("dynamic" in option_keys or "dynamic_onnx" in option_keys)
            and (
                capabilities.supports_dynamic_batch
                or capabilities.supports_dynamic_height
                or capabilities.supports_dynamic_width
            )
        ) and not is_sam2
        self.dynamic_box.setVisible(is_onnx and has_dynamic)
        self.dynamic_input_check.setVisible(
            has_dynamic
            and "dynamic" in option_keys
            and not is_onnx
            and capabilities.supports_dynamic_batch
        )
        self.dynamic_batch_check.setVisible(False)
        self.dynamic_height_check.setVisible(False)
        self.dynamic_width_check.setVisible(False)
        onnx_dynamic_visible = (
            has_dynamic
            and "dynamic_onnx" in option_keys
            and is_onnx
            and capabilities.supports_dynamic_batch
        )
        self.onnx_dynamic_batch_check.setVisible(onnx_dynamic_visible)
        self.onnx_dynamic_size_check.setVisible(
            onnx_dynamic_visible
            and (
                capabilities.supports_dynamic_height
                or capabilities.supports_dynamic_width
            )
        )
        self.onnx_dynamic_batch_check.setEnabled(not self.is_exporting)
        self.onnx_dynamic_size_check.setEnabled(not self.is_exporting)
        self.dynamic_input_check.setEnabled(not self.is_exporting)

        self.nms_box.setVisible("nms" in option_keys and capabilities.supports_nms)
        self.agnostic_nms_check.setVisible(
            "nms" in option_keys and capabilities.supports_nms
        )
        self.nms_check.setEnabled(not self.is_exporting)
        self.agnostic_nms_check.setEnabled(not self.is_exporting)
        arrange_basic_option_row(self, spec.argument)

        precision = {"FP16": "fp16", "INT8": "int8"}.get(
            self.precision_combo.currentText(), "fp32"
        )
        optimize_enabled = (
            capabilities.supports_optimize
            and precision != "fp16"
            and not self.is_exporting
        )
        if (
            capabilities.supports_optimize
            and precision == "fp16"
            and self.optimize_check.isChecked()
        ):
            self.optimize_check.setChecked(False)
        self.optimize_check.setEnabled(optimize_enabled)
        int8_enabled = self.precision_combo.currentText() == "INT8"
        self.int8_box.setVisible(
            "int8" in option_keys
            and int8_enabled
            and capabilities.supports_calibration
        )
        self.validate_quantized_box.setVisible(
            int8_enabled and capabilities.supports_quantized_validation
        )
        self.validation_samples_box.setVisible(
            int8_enabled and capabilities.supports_quantized_validation
        )
        self.simplify_check.setEnabled(
            capabilities.supports_simplify and not self.is_exporting
        )
        QTimer.singleShot(0, self, self._reflow_layout)

    @staticmethod
    def _uses_unified_dynamic_input(
        export_format: str, model_kind: str | None = None
    ) -> bool:
        return availability_helpers.uses_unified_dynamic_input(export_format, model_kind)

    @staticmethod
    def _set_line_edit(edit, value: str) -> None:
        availability_helpers.set_line_edit(edit, value)

    @staticmethod
    def _set_spin_value(spin, value) -> None:
        availability_helpers.set_spin_value(spin, value)

    def _set_precision_items(
        self,
        precisions: tuple[str, ...],
        export_format: str,
        model_kind: str,
    ):
        availability_helpers.set_precision_items(
            self, precisions, export_format, model_kind
        )

    def _current_model_kind(self) -> str:
        return availability_helpers.current_model_kind(self)

    def _update_format_availability(self, model_kind: str) -> None:
        availability_helpers.update_format_availability(self, model_kind)


__all__ = ["ModelExportVisibilityMixin"]
