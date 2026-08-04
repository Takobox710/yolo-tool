from __future__ import annotations

from pathlib import Path

from src.services.model_export import model_kind_from_path, resolve_export_format


def uses_unified_dynamic_input(export_format: str, model_kind: str | None = None) -> bool:
    return export_format != "onnx" and model_kind != "sam2"


def set_line_edit(edit, value: str) -> None:
    edit.blockSignals(True)
    edit.setText(value)
    edit.blockSignals(False)


def set_spin_value(spin, value) -> None:
    spin.blockSignals(True)
    spin.setValue(value)
    spin.blockSignals(False)


def set_precision_items(page, precisions: tuple[str, ...], export_format: str, model_kind: str) -> None:
    labels = {"fp32": "FP32", "fp16": "FP16", "int8": "INT8"}
    current = page.precision_combo.currentText()
    current_value = {value: key for key, value in labels.items()}.get(current, "fp32")
    page.precision_combo.blockSignals(True)
    page.precision_combo.clear()
    page.precision_combo.addItems([labels[item] for item in precisions])
    model = page.precision_combo.model()
    for index, precision in enumerate(precisions):
        item = model.item(index)
        if item is None:
            continue
        available = True
        if export_format == "torchscript" and precision == "fp16":
            available = page._runtime_capability_for(
                export_format, model_kind, precision
            ).available
        item.setEnabled(available)
    selected_value = "fp32"
    if current_value in precisions:
        current_index = precisions.index(current_value)
        if model.item(current_index) is not None and model.item(current_index).isEnabled():
            page.precision_combo.setCurrentText(labels[current_value])
            selected_value = current_value
        else:
            page.precision_combo.setCurrentIndex(0)
            selected_value = precisions[0]
    else:
        page.precision_combo.setCurrentIndex(0)
        selected_value = precisions[0]
    page.precision_combo.blockSignals(False)
    if selected_value != current_value:
        page.update_setting("model_export", "precision", value=selected_value)


def current_model_kind(page) -> str:
    text = page.model_combo.currentText().strip()
    if not text:
        return "yolo"
    return model_kind_from_path(Path(page.model_path_from_text(text)))


def update_format_availability(page, model_kind: str) -> None:
    model = page.format_combo.model()
    for index in range(page.format_combo.count()):
        item = model.item(index)
        if item is None:
            continue
        spec = resolve_export_format(page.format_combo.itemText(index))
        enabled = model_kind != "sam2" or spec.argument == "onnx"
        if enabled and spec.argument == "engine":
            capability = page._runtime_capability_for(
                spec.argument, model_kind, "fp32"
            )
            enabled = capability.available or not any(
                marker in capability.reason for marker in ("GPU", "CPU 版")
            )
        item.setEnabled(enabled)
