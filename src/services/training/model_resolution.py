from __future__ import annotations

from src.shared.paths import ROOT
from src.services.training.commands import (
    app_cli_command,
    build_export_command as _build_export_command,
    build_train_command as _build_train_command,
    build_val_command as _build_val_command,
    repair_validation_path_if_needed,
)
from src.services.training.model_catalog import (
    find_model_yaml_files,
    find_training_model_names as _find_training_model_names,
    find_training_model_paths as _find_training_model_paths,
    infer_task_mode_from_config,
    infer_task_mode_from_model,
    is_dataset_yaml,
    read_yaml_mapping as _read_yaml_mapping,
    resolve_training_model_reference as _resolve_training_model_reference,
    select_training_model,
    training_model_dirs as _training_model_dirs,
)
from src.services.training.results_reader import (
    latest_result_csv,
    read_results_csv_for_curves,
    read_train_metrics,
)


def training_model_dirs(project_root, app_root=None):
    return _training_model_dirs(project_root, ROOT if app_root is None else app_root)


def find_training_model_paths(project_root, app_root=None):
    return _find_training_model_paths(project_root, ROOT if app_root is None else app_root)


def find_training_model_names(project_root, app_root=None):
    return _find_training_model_names(project_root, ROOT if app_root is None else app_root)


def resolve_training_model_reference(model_text, project_root, app_root=None):
    return _resolve_training_model_reference(
        model_text, project_root, ROOT if app_root is None else app_root
    )


def build_train_command(config):
    return _build_train_command(config)


def build_export_command(model_path, export_format, imgsz=640):
    return _build_export_command(model_path, export_format, imgsz)


def build_val_command(config):
    return _build_val_command(config)


