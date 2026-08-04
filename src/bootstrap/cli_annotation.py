from __future__ import annotations

from src.bootstrap.cli_annotation_batch import _run_ai_label_cli_impl
from src.bootstrap.cli_annotation_labels import _run_model_labels_cli_impl
from src.bootstrap.cli_annotation_runtime import _run_ai_runtime_cli_impl
from src.bootstrap.cli_sam_runtime import _run_sam_assist_runtime_cli_impl


def run_model_labels(argv: list[str]) -> int:
    return _run_model_labels_cli_impl(argv)


def run_ai_label(argv: list[str]) -> int:
    return _run_ai_label_cli_impl(argv)


def run_ai_runtime(argv: list[str]) -> int:
    return _run_ai_runtime_cli_impl(argv)


def run_sam_assist_runtime(argv: list[str]) -> int:
    return _run_sam_assist_runtime_cli_impl(argv)


__all__ = ["run_ai_label", "run_ai_runtime", "run_model_labels", "run_sam_assist_runtime"]
