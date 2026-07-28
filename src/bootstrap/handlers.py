from __future__ import annotations

from collections.abc import Callable


def _legacy_handler(name: str) -> Callable[[list[str]], int]:
    """Load CLI implementation lazily so GUI startup never imports Ultralytics."""
    def handler(argv: list[str]) -> int:
        from src import train_cli

        return getattr(train_cli, f"_run_{name}_impl")(argv)

    return handler


run_train = _legacy_handler("train_cli")
run_export = _legacy_handler("export_cli")
run_export_probe = _legacy_handler("export_probe_cli")
run_install_model_export_package = _legacy_handler("install_model_export_package_cli")
run_migrate_legacy_extension = _legacy_handler("migrate_legacy_extension_cli")
run_runtime_probe = _legacy_handler("runtime_probe_cli")
run_remove_managed_models = _legacy_handler("remove_managed_models_cli")
run_val = _legacy_handler("val_cli")
run_model_labels = _legacy_handler("model_labels_cli")
run_predict = _legacy_handler("predict_cli")
run_ai_label = _legacy_handler("ai_label_cli")
run_ai_runtime = _legacy_handler("ai_runtime_cli")
run_sam_assist_runtime = _legacy_handler("sam_assist_runtime_cli")


__all__ = [
    "run_ai_label",
    "run_ai_runtime",
    "run_export",
    "run_export_probe",
    "run_install_model_export_package",
    "run_migrate_legacy_extension",
    "run_model_labels",
    "run_predict",
    "run_remove_managed_models",
    "run_runtime_probe",
    "run_sam_assist_runtime",
    "run_train",
    "run_val",
]
