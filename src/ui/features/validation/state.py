"""Compatibility exports for validation page state.

New code should import the domain module that owns the operation.  This
facade remains so existing page mixins and external extensions keep working.
"""

from src.ui.features.validation.config_state import (
    config,
    detection_config_or_warn,
    get_model_path,
    prepare_temporary_validation_yaml,
    restore_temporary_validation_yaml_if_needed,
    single_file_config,
)
from src.ui.features.validation.log_state import (
    append_active_log,
    clear_active_log,
    handle_video_progress,
)
from src.ui.features.validation.mode_state import (
    is_video_detection_mode,
    update_source_mode,
    update_video_mode_controls,
)
from src.ui.features.validation.persistence_state import (
    connect_validation_persistence,
    handle_data_path_changed,
    handle_source_input_changed,
    handle_source_scope_changed,
    persist_validation_integer,
    persist_validation_model,
    persist_validation_numeric,
    persist_validation_value,
)
from src.ui.features.validation.source_state import (
    dataset_split_dir,
    folder_source_path_for_page,
    refresh_model_choices,
    refresh_source_items,
    resolve_combo_path_text,
    scope_target_path_for_page,
)

from src.ui.features.validation._state_impl import (
    dataset_yaml_root_for_page,
    val_override_value_for_scope,
)

__all__ = [
    "append_active_log",
    "clear_active_log",
    "config",
    "connect_validation_persistence",
    "dataset_split_dir",
    "dataset_yaml_root_for_page",
    "detection_config_or_warn",
    "folder_source_path_for_page",
    "get_model_path",
    "handle_data_path_changed",
    "handle_source_input_changed",
    "handle_source_scope_changed",
    "handle_video_progress",
    "is_video_detection_mode",
    "persist_validation_integer",
    "persist_validation_model",
    "persist_validation_numeric",
    "persist_validation_value",
    "prepare_temporary_validation_yaml",
    "refresh_model_choices",
    "refresh_source_items",
    "resolve_combo_path_text",
    "restore_temporary_validation_yaml_if_needed",
    "scope_target_path_for_page",
    "single_file_config",
    "update_source_mode",
    "update_video_mode_controls",
    "val_override_value_for_scope",
]
