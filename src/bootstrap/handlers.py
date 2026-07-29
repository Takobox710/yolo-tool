from __future__ import annotations


def run_train(argv: list[str]) -> int:
    from src.bootstrap.cli_training import run_train as handler

    return handler(argv)


def run_val(argv: list[str]) -> int:
    from src.bootstrap.cli_validation import run_val as handler

    return handler(argv)


def run_predict(argv: list[str]) -> int:
    from src.bootstrap.cli_validation import run_predict as handler

    return handler(argv)


def run_export(argv: list[str]) -> int:
    from src.bootstrap.cli_model_export import run_export as handler

    return handler(argv)


def run_export_probe(argv: list[str]) -> int:
    from src.bootstrap.cli_model_export import run_export_probe as handler

    return handler(argv)


def run_install_model_export_package(argv: list[str]) -> int:
    from src.bootstrap.cli_model_export import run_install_model_export_package as handler

    return handler(argv)


def run_migrate_legacy_extension(argv: list[str]) -> int:
    from src.bootstrap.cli_model_export import run_migrate_legacy_extension as handler

    return handler(argv)


def run_runtime_probe(argv: list[str]) -> int:
    from src.bootstrap.cli_runtime import run_runtime_probe as handler

    return handler(argv)


def run_remove_managed_models(argv: list[str]) -> int:
    from src.bootstrap.cli_runtime import run_remove_managed_models as handler

    return handler(argv)


def run_model_labels(argv: list[str]) -> int:
    from src.bootstrap.cli_annotation import run_model_labels as handler

    return handler(argv)


def run_ai_label(argv: list[str]) -> int:
    from src.bootstrap.cli_annotation import run_ai_label as handler

    return handler(argv)


def run_ai_runtime(argv: list[str]) -> int:
    from src.bootstrap.cli_annotation import run_ai_runtime as handler

    return handler(argv)


def run_sam_assist_runtime(argv: list[str]) -> int:
    from src.bootstrap.cli_annotation import run_sam_assist_runtime as handler

    return handler(argv)


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
