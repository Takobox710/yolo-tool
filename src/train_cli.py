from __future__ import annotations

from typing import Any

from src.bootstrap.cli_common import (
    _emit_structured as _cli_emit_structured,
    _load_json_payload as _cli_load_json_payload,
    _parse_key_values as _cli_parse_key_values,
    _parse_value as _cli_parse_value,
)
from src.bootstrap.cli_annotation import (
    run_ai_label as _run_ai_label,
    run_ai_runtime as _run_ai_runtime,
    run_model_labels as _run_model_labels,
    run_sam_assist_runtime as _run_sam_assist_runtime,
)
from src.bootstrap.cli_model_export import (
    run_export as _run_export,
    run_export_probe as _run_export_probe,
    run_install_model_export_package as _run_install_model_export_package,
    run_migrate_legacy_extension as _run_migrate_legacy_extension,
)
from src.bootstrap.cli_runtime import (
    run_remove_managed_models as _run_remove_managed_models,
    run_runtime_probe as _run_runtime_probe,
)
from src.bootstrap.cli_training import run_train as _run_train
from src.bootstrap.cli_validation import run_predict as _run_predict
from src.bootstrap.cli_validation import run_val as _run_val


def _parse_value(raw: str) -> Any:
    return _cli_parse_value(raw)


def _parse_key_values(parts: list[str]) -> dict[str, Any]:
    return _cli_parse_key_values(parts)


def _emit_structured(event: str, **payload: Any) -> None:
    _cli_emit_structured(event, **payload)


def _load_json_payload(argv: list[str], usage: str) -> dict[str, Any]:
    return _cli_load_json_payload(argv, usage)


def run_train_cli(argv: list[str]) -> int:
    return _run_train(argv)


def run_export_cli(argv: list[str]) -> int:
    return _run_export(argv)


def run_export_probe_cli(argv: list[str]) -> int:
    return _run_export_probe(argv)


def run_install_model_export_package_cli(argv: list[str]) -> int:
    return _run_install_model_export_package(argv)


def run_migrate_legacy_extension_cli(argv: list[str]) -> int:
    return _run_migrate_legacy_extension(argv)


def run_runtime_probe_cli(argv: list[str]) -> int:
    return _run_runtime_probe(argv)


def run_remove_managed_models_cli(argv: list[str]) -> int:
    return _run_remove_managed_models(argv)


def run_val_cli(argv: list[str]) -> int:
    return _run_val(argv)


def run_model_labels_cli(argv: list[str]) -> int:
    return _run_model_labels(argv)


def run_predict_cli(argv: list[str]) -> int:
    return _run_predict(argv, emit=_emit_structured)


def run_ai_label_cli(argv: list[str]) -> int:
    return _run_ai_label(argv)


def run_ai_runtime_cli(argv: list[str]) -> int:
    return _run_ai_runtime(argv)


def run_sam_assist_runtime_cli(argv: list[str]) -> int:
    return _run_sam_assist_runtime(argv)


__all__ = [
    "_emit_structured",
    "_load_json_payload",
    "_parse_key_values",
    "_parse_value",
    "run_ai_label_cli",
    "run_ai_runtime_cli",
    "run_export_cli",
    "run_export_probe_cli",
    "run_install_model_export_package_cli",
    "run_migrate_legacy_extension_cli",
    "run_model_labels_cli",
    "run_predict_cli",
    "run_remove_managed_models_cli",
    "run_runtime_probe_cli",
    "run_sam_assist_runtime_cli",
    "run_train_cli",
    "run_val_cli",
]
