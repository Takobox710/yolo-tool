from __future__ import annotations

from pathlib import Path

from src.services.data_ops import (
    relative_path_from_project,
    resolve_project_path,
    simplified_model_path,
)
from src.services.validation import is_live_source_mode
from src.shared.qt import QMessageBox, Qt
from src.ui.features.validation.helpers import dataset_yaml_root, validation_val_override
from src.ui.features.validation.models import build_validation_model_choices
from src.ui.features.validation.sources import (
    CUSTOM_SOURCE_OPTIONS,
    IMAGE_SOURCE_OPTIONS,
    SOURCE_SCOPE_OPTIONS,
    VIDEO_SOURCE_OPTIONS,
    collect_validation_source_items,
    dataset_split_image_dir,
    folder_source_path_for_selection,
    scope_target_path,
)


def update_source_mode(page, value):
    page.detection_started_for_source = False
    page.clear_validation_previews()
    layouts = [
        getattr(page, name, None)
        for name in (
            "validation_layout",
            "validation_split_layout",
            "left_column_layout",
            "validation_right_layout",
            "validation_views_layout",
        )
    ]
    layouts.extend(
        panel.layout
        for panel in (
            getattr(page, "source_panel", None),
            getattr(page, "result_panel", None),
        )
        if panel is not None
    )
    layouts = [layout for layout in layouts if layout is not None]
    page.setUpdatesEnabled(False)
    for layout in layouts:
        layout.setEnabled(False)
    try:
        camera = is_live_source_mode(value)
        image_folder_mode = value == "图片检测"
        video_folder_mode = value == "视频检测"
        folder_source_mode = image_folder_mode or video_folder_mode
        val_mode = page.is_val_mode(value)
        page.source_box.setVisible(folder_source_mode)
        page.data_box.setVisible(val_mode)
        page.source_scope_box.setVisible(val_mode)
        page.camera_box.setVisible(camera)
        page.save_box.setVisible(True)
        page.open_val_save_btn.setVisible(val_mode)
        page.set_result_navigation_enabled((not camera) and (not val_mode))
        page.detect_log.setVisible(not val_mode)
        log_index = page.left_column_layout.indexOf(page.detect_log)
        if log_index >= 0:
            page.left_column_layout.setStretch(log_index, 0 if val_mode else 1)
        page.left_column_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop if val_mode else Qt.AlignmentFlag(0)
        )
        page.toolbar_widget.setVisible(not val_mode and not camera)
        page.views_widget.setVisible(not val_mode)
        page.table_panel.setVisible(not val_mode)
        page.val_log_panel.setVisible(val_mode)
        if camera:
            page.counter.setText("实时预览")
        elif val_mode:
            page.counter.setText("验证模式")
        elif not page.detect_results:
            page.counter.setText("0/0")
        validation = page.app.settings.get("validation", {})
        source_path = validation.get("source_path", "")
        source_selection = validation.get("source_selection", "")
        if image_folder_mode:
            current_source = source_selection
            if current_source not in IMAGE_SOURCE_OPTIONS:
                current_source = (
                    relative_path_from_project(source_path, page.project_root())
                    if source_path
                    else validation.get("source_scope", "全部图片")
                )
            page._configure_source_combo(
                IMAGE_SOURCE_OPTIONS,
                relative_path_from_project(source_path, page.project_root())
                if source_path
                else current_source,
                "选择图片文件夹或图片文件",
            )
        elif video_folder_mode:
            page._configure_source_combo(
                VIDEO_SOURCE_OPTIONS,
                relative_path_from_project(source_path, page.project_root())
                if source_path
                else (
                    source_selection
                    if source_selection in VIDEO_SOURCE_OPTIONS
                    else "批量视频"
                ),
                "选择视频文件夹或视频文件",
            )
        page.update_detection_button_text()
        page.refresh_source_items()
        update_video_mode_controls(page)
    finally:
        for layout in reversed(layouts):
            layout.setEnabled(True)
        for layout in layouts:
            layout.activate()
        page.setUpdatesEnabled(True)
        page.updateGeometry()
        page.update()


def is_video_detection_mode(page) -> bool:
    mode = page.mode_combo.currentText()
    return mode == "视频检测"


def update_video_mode_controls(page) -> None:
    video_mode = is_video_detection_mode(page)
    detection_mode = not page.is_val_mode()
    live_mode = is_live_source_mode(page.mode_combo.currentText())
    page.result_nav_widget.setVisible(detection_mode and not video_mode and not live_mode)
    page.video_progress_widget.setVisible(detection_mode and video_mode)
    page.start_det_btn.setVisible(True)
    page.stop_det_btn.setVisible(True)
    page.video_play_btn.setVisible(video_mode)
    page.video_prev_btn.setVisible(video_mode)
    page.video_next_btn.setVisible(video_mode)
    page.source_view.setVisible(not video_mode)
    page.result_view.setVisible(not video_mode)
    page.source_video_player.setVisible(video_mode)
    page.result_video_player.setVisible(video_mode)
    if not video_mode:
        page.video_play_btn.blockSignals(True)
        page.video_play_btn.setChecked(False)
        page.video_play_btn.blockSignals(False)
        page.stop_video_playback()
    elif page.source_items:
        page.load_video_source(page.source_items[page.source_index])


def refresh_source_items(page):
    page.source_items = collect_validation_source_items(
        mode=page.mode_combo.currentText(),
        is_val_mode=page.is_val_mode(),
        source_text=page.source_combo.currentText(),
        paths_settings=page.app.settings["paths"],
        resolve_text=page.resolve_combo_path_text,
        selected_source_path=page.app.settings.get("validation", {}).get(
            "source_path", ""
        ),
    )
    if not page.source_items:
        page.source_index = -1
        if (
            page.mode_combo.currentText() == "图片检测"
            and not page.detection_started_for_source
        ):
            page.counter.setText("0/0")
        return
    if page.source_index < 0 or page.source_index >= len(page.source_items):
        page.source_index = 0
    if (
        page.mode_combo.currentText() == "图片检测"
        and not page.detection_started_for_source
    ):
        page.show_source_preview(page.source_items[page.source_index])


def dataset_split_dir(page, split: str) -> Path:
    return dataset_split_image_dir(Path(page.app.settings["paths"]["dataset_dir"]), split)


def scope_target_path_for_page(page, scope: str) -> Path:
    if str(scope).strip() not in SOURCE_SCOPE_OPTIONS:
        return Path(page.resolve_combo_path_text(scope)).resolve()
    return scope_target_path(scope, page.app.settings["paths"])


def folder_source_path_for_page(page) -> str:
    return folder_source_path_for_selection(
        page.source_combo.currentText(),
        page.app.settings["paths"],
        page.resolve_combo_path_text,
        page.app.settings.get("validation", {}).get("source_path", ""),
    )


def refresh_model_choices(page, preferred_model: str | None = None):
    current_text = preferred_model
    if current_text is None:
        current_text = page.model_combo.currentText()
    project_root = page.project_root()
    result_dir = Path(page.app.settings["paths"]["result_dir"])
    show_last = page.app.settings.get("features", {}).get(
        "show_last_training_models", False
    )
    choices = build_validation_model_choices(
        current_text=current_text,
        current_display_paths=page._model_display_paths,
        project_root=project_root,
        result_dir=result_dir,
        show_last_training_models=show_last,
        resolve_text=page.resolve_combo_path_text,
    )
    page._all_model_paths = choices.all_paths
    page._model_display_paths = choices.display_paths
    page.model_combo.blockSignals(True)
    page.model_combo.clear()
    page.model_combo.addItems(choices.display_names)
    page.model_combo.setCurrentText(choices.selected_display)
    page.model_combo.blockSignals(False)


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
    page.app.settings.setdefault("validation", {})["model_path"] = page._get_model_path()
    page.save_settings()


def persist_validation_value(page, key: str, value):
    page.app.settings.setdefault("validation", {})[key] = value
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
    update_video_mode_controls(page)


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


def get_model_path(page) -> str:
    text = page.model_combo.currentText()
    mapped = page._model_display_paths.get(text)
    if mapped is not None:
        return str(mapped)
    for p in page._all_model_paths:
        if (
            simplified_model_path(str(p), page.project_root()) == text
            or page.display_path(p) == text
            or str(p) == text
        ):
            return str(p)
    if Path(text).exists():
        return text
    resolved = page.resolve_combo_path_text(text)
    return resolved if resolved else text


def resolve_combo_path_text(page, text: str) -> str:
    return resolve_project_path(text, page.project_root())


def config(page):
    model_path = page._get_model_path()
    try:
        confidence = float(page.conf_edit.text())
    except ValueError as exc:
        raise ValueError("置信度必须是数字。") from exc
    try:
        iou = float(page.iou_edit.text())
    except ValueError as exc:
        raise ValueError("IoU 必须是数字。") from exc
    try:
        imgsz = int(page.imgsz_combo.currentText())
    except ValueError as exc:
        raise ValueError("图片尺寸必须是整数。") from exc
    return {
        "model_path": model_path,
        "source_mode": page.mode_combo.currentText(),
        "source_path": page._folder_source_path_for_selection()
        if page.mode_combo.currentText() in {"图片检测", "视频检测"}
        else page.resolve_combo_path_text(page.source_combo.currentText()),
        "data": page.resolve_path_text(page.data_edit),
        "source_scope": page.source_scope_combo.currentText(),
        "camera_index": int(page.camera_combo.currentText()),
        "confidence": confidence,
        "iou": iou,
        "imgsz": imgsz,
        "save_dir": page.resolve_path_text(page.save_edit),
    }


def detection_config_or_warn(page) -> dict | None:
    try:
        config_value = page.config()
    except ValueError as exc:
        QMessageBox.information(page, "参数无效", str(exc))
        return None
    if not str(config_value.get("model_path") or "").strip():
        QMessageBox.information(page, "模型为空", "请选择一个用于检测的模型。")
        return None
    if (
        not is_live_source_mode(config_value.get("source_mode", ""))
        and not str(config_value.get("source_path") or "").strip()
    ):
        QMessageBox.information(page, "输入源为空", "请先选择有效的输入源。")
        return None
    return config_value


def single_file_config(page, path: Path, base_config: dict | None = None) -> dict:
    config_value = dict(base_config or page.config())
    config_value["source_mode"] = "图片/视频"
    config_value["source_path"] = str(path)
    return config_value


def dataset_yaml_root_for_page(payload: dict, data_path: Path) -> Path:
    return dataset_yaml_root(payload, data_path)


def val_override_value_for_scope(page, data_path: Path, scope: str) -> str:
    target = page._scope_target_path(scope)
    images_dir = Path(page.app.settings["paths"]["images_dir"]).resolve()
    return validation_val_override(data_path, scope, target, images_dir)


def prepare_temporary_validation_yaml(page, data_path: Path, scope: str) -> None:
    page.validation_yaml_patch.prepare(
        data_path,
        page._val_override_value_for_scope(data_path, scope),
    )


def restore_temporary_validation_yaml_if_needed(page) -> None:
    page.validation_yaml_patch.restore_if_needed()


def clear_active_log(page):
    page.detect_log.clear()
    page.val_log.clear()


def append_active_log(page, text: str):
    if page.is_val_mode():
        page.val_log.append(text)
        return
    page.detect_log.append(text)


def handle_video_progress(page, payload: dict):
    percent = max(0, min(100, int(payload.get("percent") or 0)))
    frame = int(payload.get("frame") or 0)
    total_frames = int(payload.get("total_frames") or 0)
    frames_last_second = int(payload.get("frames_last_second") or 0)
    if total_frames:
        message = (
            f"视频检测进度：{percent}%（{frame}/{total_frames}帧） | "
            f"上一秒：{frames_last_second}帧"
        )
    else:
        message = f"视频检测进度：{percent}% | 上一秒：{frames_last_second}帧"
    page.append_active_log(message)
    page.set_status_text(message)


