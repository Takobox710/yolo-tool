from __future__ import annotations


def run_app() -> None:
    from src.bootstrap.app_factory import run_app as ui_run_app

    ui_run_app()

