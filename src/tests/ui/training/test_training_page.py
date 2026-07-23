from pathlib import Path

import os

import subprocess

import sys

from types import SimpleNamespace

from src.tests.helpers.ui_paths import (
    APP,
    DATA_VIEW,
    HOME_VIEW,
    ICON_ICO,
    ICON_PNG,
    INSTALLER_ISS,
    PACKAGING_DOC,
    PACKAGING_ONE_CLICK_SCRIPT,
    PACKAGING_SCRIPT,
    PACKAGING_SPEC,
    PAGE_BASE,
    SETTINGS_VIEW,
    TRAIN_VIEW,
    UI_BUNDLE_PATHS,
    VALIDATE_VIEW,
    WINDOW,
)


def _read_app():
    return APP.read_text(encoding="utf-8")

def _read_ui_bundle():
    return "\n".join(path.read_text(encoding="utf-8") for path in UI_BUNDLE_PATHS)


def test_training_page_persists_updated_fields_to_settings(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.training.page import TrainPage

    app = QApplication.instance() or QApplication([])
    saved = {}
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda data: saved.update(data)),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
    )

    page = TrainPage(fake_app)
    page.edits["epochs"].setText("123")
    page.pretrained_combo.setCurrentText("custom.pt")

    assert fake_app.settings["training"]["epochs"] == "123"
    assert Path(fake_app.settings["training"]["pretrained"]).name == "custom.pt"
    assert "training" in saved


def test_train_page_stop_flow_recovers_buttons_and_hides_stop_noise(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.training import page as training_view
    from src.ui.features.training.page import TrainPage

    class FakeStatus:
        def __init__(self):
            self.text = ""

        def setText(self, value):
            self.text = value

    class FakeProcess:
        def __init__(self):
            self.returncode = None

        def poll(self):
            return self.returncode

    class FakeHandle:
        def __init__(self):
            self.process = FakeProcess()
            self.thread = None

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    settings["features"]["custom_command_dialog"] = False
    fake_status = FakeStatus()
    fake_handle = FakeHandle()
    stop_calls = {"count": 0}

    def fake_spawn(_command, _cwd, _queue):
        return fake_handle

    def fake_stop(_handle):
        stop_calls["count"] += 1
        fake_handle.process.returncode = 1

    monkeypatch.setattr(training_view, "spawn_logged_process", fake_spawn)
    monkeypatch.setattr(training_view, "stop_process", fake_stop)

    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=fake_status,
        training_handle=None,
    )

    page = TrainPage(fake_app)
    page.start()

    assert page.is_training is True
    assert page.start_btn.isEnabled() is False
    assert page.stop_btn.isEnabled() is True

    page.stop()
    page.log_queue.put(("log", "Traceback (most recent call last):"))
    page.log_queue.put(("log", "PermissionError: [WinError 5] Access is denied"))
    page.log_queue.put(("exit", 1))
    page.poll_training_queue()

    log_text = page.log.toPlainText()

    assert stop_calls["count"] == 1
    assert page.is_training is False
    assert page.start_btn.isEnabled() is True
    assert page.stop_btn.isEnabled() is False
    assert fake_app.training_handle is None
    assert fake_status.text == "训练已停止"
    assert "已请求停止训练。" in log_text
    assert "训练已停止。" in log_text
    assert "Traceback (most recent call last):" not in log_text
    assert "PermissionError: [WinError 5]" not in log_text


def test_train_page_recovers_if_process_exits_without_queue_exit_event(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.training import page as training_view
    from src.ui.features.training.page import TrainPage

    class FakeStatus:
        def __init__(self):
            self.text = ""

        def setText(self, value):
            self.text = value

    class FakeProcess:
        def __init__(self):
            self.returncode = None

        def poll(self):
            return self.returncode

    class FakeHandle:
        def __init__(self):
            self.process = FakeProcess()
            self.thread = None

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    settings["features"]["custom_command_dialog"] = False
    fake_status = FakeStatus()
    fake_handle = FakeHandle()

    monkeypatch.setattr(
        training_view,
        "spawn_logged_process",
        lambda _command, _cwd, _queue: fake_handle,
    )

    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=fake_status,
        training_handle=None,
    )

    page = TrainPage(fake_app)
    page.start()
    fake_handle.process.returncode = 1
    page.poll_training_queue()

    assert page.is_training is False
    assert page.start_btn.isEnabled() is True
    assert page.stop_btn.isEnabled() is False
    assert fake_app.training_handle is None
    assert fake_status.text == "训练异常结束"
