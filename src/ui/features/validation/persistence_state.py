from __future__ import annotations

from src.ui.features.validation.sources import CUSTOM_SOURCE_OPTIONS, SOURCE_SCOPE_OPTIONS


def connect_validation_persistence(page):
    if getattr(page, "_persistence_connected", False):
        return
    page._persistence_connected = True
    page.model_combo.currentTextChanged.connect(page._persist_validation_model)
    page.mode_combo.currentTextChanged.connect(
        lambda value: page._persist_validation_value("source_mode", value)
    )
    page.source_combo.currentTextChanged.connect(lambda _text: page._handle_source_input_changed())
    page.data_edit.textChanged.connect(lambda _text: page._handle_data_path_changed())
    page.source_scope_combo.currentTextChanged.connect(
        lambda value: page._handle_source_scope_changed(value)
    )
    page.save_edit.textChanged.connect(
        lambda _text: page._persist_validation_value(
            "save_dir", page.resolve_path_text(page.save_edit)
        )
    )
    page.camera_combo.currentTextChanged.connect(
        lambda value: page._persist_validation_value("camera_index", int(value))
    )
    page.conf_edit.textChanged.connect(
        lambda text: page._persist_validation_numeric("confidence", text)
    )
    page.iou_edit.textChanged.connect(
        lambda text: page._persist_validation_numeric("iou", text)
    )
    page.imgsz_combo.currentTextChanged.connect(
        lambda text: page._persist_validation_integer("imgsz", text)
    )


def persist_validation_model(page, _text: str = ""):
    page.context.settings.validation.model_path = page._get_model_path()
    page.save_settings()


def persist_validation_value(page, key: str, value):
    setattr(page.context.settings.validation, key, value)
    page.save_settings()


def handle_source_input_changed(page):
    text = page.source_combo.currentText().strip()
    page.detection_started_for_source = False
    page.source_index = -1
    page.clear_validation_previews()
    if text in SOURCE_SCOPE_OPTIONS:
        if page.mode_combo.currentText() == "图片检测":
            page._persist_validation_value("source_scope", text)
        page._persist_validation_value("source_selection", "")
        page._persist_validation_value("source_path", "")
    elif text in CUSTOM_SOURCE_OPTIONS:
        page._persist_validation_value("source_selection", text)
        page._persist_validation_value("source_path", "")
    else:
        page._persist_validation_value("source_selection", "")
        page._persist_validation_value("source_path", page.resolve_combo_path_text(text))
    page.refresh_source_items()
    page.update_video_mode_controls()


def handle_data_path_changed(page):
    page._persist_validation_value("data", page.resolve_path_text(page.data_edit))
    page.refresh_source_items()


def handle_source_scope_changed(page, value: str):
    page._persist_validation_value("source_scope", value)
    page.refresh_source_items()


def persist_validation_numeric(page, key: str, text: str):
    try:
        value = float(text)
    except ValueError:
        value = text
    page._persist_validation_value(key, value)


def persist_validation_integer(page, key: str, text: str):
    try:
        value = int(text)
    except ValueError:
        value = text
    page._persist_validation_value(key, value)


__all__ = [
    "connect_validation_persistence",
    "handle_data_path_changed",
    "handle_source_input_changed",
    "handle_source_scope_changed",
    "persist_validation_integer",
    "persist_validation_model",
    "persist_validation_numeric",
    "persist_validation_value",
]
