from __future__ import annotations

from pathlib import Path

from src.services.data_ops import relative_path_from_project, resolve_project_path, simplified_model_path
from src.ui.features.validation.models import build_validation_model_choices
from src.ui.features.validation.sources import (
    SOURCE_SCOPE_OPTIONS,
    collect_validation_source_items,
    dataset_split_image_dir,
    folder_source_path_for_selection,
    scope_target_path,
)


def refresh_source_items(page):
    page.source_items = collect_validation_source_items(
        mode=page.mode_combo.currentText(),
        is_val_mode=page.is_val_mode(),
        source_text=page.source_combo.currentText(),
        paths_settings=page.context.settings.paths,
        resolve_text=page.resolve_combo_path_text,
        selected_source_path=page.context.settings.validation.source_path,
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
    return dataset_split_image_dir(Path(page.context.settings.paths.dataset_dir), split)


def scope_target_path_for_page(page, scope: str) -> Path:
    if str(scope).strip() not in SOURCE_SCOPE_OPTIONS:
        return Path(page.resolve_combo_path_text(scope)).resolve()
    return scope_target_path(scope, page.context.settings.paths)


def folder_source_path_for_page(page) -> str:
    return folder_source_path_for_selection(
        page.source_combo.currentText(),
        page.context.settings.paths,
        page.resolve_combo_path_text,
        page.context.settings.validation.source_path,
    )


def refresh_model_choices(page, preferred_model: str | None = None):
    current_text = preferred_model
    if current_text is None:
        current_text = page.model_combo.currentText()
    choices = build_validation_model_choices(
        current_text=current_text,
        current_display_paths=page._model_display_paths,
        project_root=page.project_root(),
        result_dir=Path(page.context.settings.paths.result_dir),
        show_last_training_models=page.context.settings.features.show_last_training_models,
        resolve_text=page.resolve_combo_path_text,
    )
    page._all_model_paths = choices.all_paths
    page._model_display_paths = choices.display_paths
    page.model_combo.blockSignals(True)
    page.model_combo.clear()
    page.model_combo.addItems(choices.display_names)
    page.model_combo.setCurrentText(choices.selected_display)
    page.model_combo.blockSignals(False)


def resolve_combo_path_text(page, text: str) -> str:
    return resolve_project_path(text, page.project_root())


__all__ = [
    "dataset_split_dir",
    "folder_source_path_for_page",
    "refresh_model_choices",
    "refresh_source_items",
    "resolve_combo_path_text",
    "scope_target_path_for_page",
]
