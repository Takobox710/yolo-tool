from __future__ import annotations

from pathlib import Path

from src.services.data_ops import simplified_model_path
from src.services.validation import is_live_source_mode
from src.shared.qt import QMessageBox
from src.ui.features.validation.helpers import dataset_yaml_root, validation_val_override


def get_model_path(page) -> str:
    text = page.model_combo.currentText()
    mapped = page._model_display_paths.get(text)
    if mapped is not None:
        return str(mapped)
    for path in page._all_model_paths:
        if (
            simplified_model_path(str(path), page.project_root()) == text
            or page.display_path(path) == text
            or str(path) == text
        ):
            return str(path)
    if Path(text).exists():
        return text
    resolved = page.resolve_combo_path_text(text)
    return resolved if resolved else text


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
    images_dir = Path(page.context.settings.paths.images_dir).resolve()
    return validation_val_override(data_path, scope, target, images_dir)


def prepare_temporary_validation_yaml(page, data_path: Path, scope: str) -> None:
    page.validation_yaml_patch.prepare(
        data_path,
        page._val_override_value_for_scope(data_path, scope),
    )


def restore_temporary_validation_yaml_if_needed(page) -> None:
    page.validation_yaml_patch.restore_if_needed()


__all__ = [
    "config",
    "dataset_yaml_root_for_page",
    "detection_config_or_warn",
    "get_model_path",
    "prepare_temporary_validation_yaml",
    "restore_temporary_validation_yaml_if_needed",
    "single_file_config",
    "val_override_value_for_scope",
]
