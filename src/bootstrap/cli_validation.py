from __future__ import annotations

from typing import Callable

from src.bootstrap.cli_predict import _run_predict_cli_impl
from src.bootstrap.cli_val import _run_val_cli_impl


def run_val(argv: list[str]) -> int:
    return _run_val_cli_impl(argv)


def run_predict(argv: list[str], emit: Callable[..., None] | None = None) -> int:
    return _run_predict_cli_impl(argv, emit=emit)


__all__ = ["run_predict", "run_val"]
