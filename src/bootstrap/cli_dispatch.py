from __future__ import annotations

import json
from collections.abc import Callable

from src.bootstrap import handlers


CliHandler = Callable[[list[str]], int]

FLAG_HANDLERS: dict[str, CliHandler] = {
    "--yolo-train": handlers.run_train,
    "--yolo-export": handlers.run_export,
    "--yolo-export-probe": handlers.run_export_probe,
    "--install-model-export-package": handlers.run_install_model_export_package,
    "--migrate-legacy-extension": handlers.run_migrate_legacy_extension,
    "--runtime-probe": handlers.run_runtime_probe,
    "--remove-managed-models": handlers.run_remove_managed_models,
    "--yolo-val": handlers.run_val,
    "--yolo-predict": handlers.run_predict,
    "--yolo-ai-label": handlers.run_ai_label,
    "--yolo-ai-runtime": handlers.run_ai_runtime,
    "--yolo-model-labels": handlers.run_model_labels,
}


def dispatch_cli(flag: str, argv: list[str]) -> int | None:
    handler = FLAG_HANDLERS.get(flag)
    return None if handler is None else handler(argv)


def run_torch_summary_cli(argv: list[str]) -> int:
    del argv
    from src.services.runtime import preload_torch_runtime

    print(json.dumps(preload_torch_runtime(), ensure_ascii=False))
    return 0


def run_train_cli(argv: list[str]) -> int:
    return handlers.run_train(argv)


def run_export_cli(argv: list[str]) -> int:
    return handlers.run_export(argv)


def run_export_probe_cli(argv: list[str]) -> int:
    return handlers.run_export_probe(argv)


def run_install_model_export_package_cli(argv: list[str]) -> int:
    return handlers.run_install_model_export_package(argv)


def run_migrate_legacy_extension_cli(argv: list[str]) -> int:
    return handlers.run_migrate_legacy_extension(argv)


def run_runtime_probe_cli(argv: list[str]) -> int:
    return handlers.run_runtime_probe(argv)


def run_remove_managed_models_cli(argv: list[str]) -> int:
    return handlers.run_remove_managed_models(argv)


def run_val_cli(argv: list[str]) -> int:
    return handlers.run_val(argv)


def run_model_labels_cli(argv: list[str]) -> int:
    return handlers.run_model_labels(argv)


def run_predict_cli(argv: list[str]) -> int:
    return handlers.run_predict(argv)


def run_ai_label_cli(argv: list[str]) -> int:
    return handlers.run_ai_label(argv)


def run_ai_runtime_cli(argv: list[str]) -> int:
    return handlers.run_ai_runtime(argv)


__all__ = [
    "FLAG_HANDLERS",
    "dispatch_cli",
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
    "run_torch_summary_cli",
    "run_train_cli",
    "run_val_cli",
]
