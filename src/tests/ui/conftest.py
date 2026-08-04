"""Shared UI fixtures; domain-specific factories stay in domain folders."""

from types import SimpleNamespace

import pytest

from src.services.settings import build_default_settings


@pytest.fixture
def fake_app(tmp_path, qt_app):
    return SimpleNamespace(
        settings=build_default_settings(tmp_path),
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda *_args, **_kwargs: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
        workers=[],
        export_handle=None,
    )
