from pathlib import Path

import os

import subprocess

import sys

from types import SimpleNamespace

from scr.tests.helpers.ui_paths import (
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


def test_train_page_resolves_model_file_from_data_models(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.services.settings_service import build_default_settings
    from scr.services.training_service import build_train_command
    from scr.ui.qt import QApplication
    from scr.ui.views.training import TrainPage

    model_path = tmp_path / "data" / "models" / "yolov8m-obb.pt"
    model_path.parent.mkdir(parents=True)
    model_path.write_text("weights", encoding="utf-8")

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    settings["training"]["model_yaml"] = ""
    settings["training"]["pretrained"] = model_path.name
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
    )

    page = TrainPage(fake_app)
    command = build_train_command(page.collect_config())

    assert f"model={model_path}" in command
    assert f"pretrained={model_path}" in command


def test_train_page_merges_project_and_app_model_lists_with_project_priority(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.services.settings_service import build_default_settings
    from scr.services import training_service
    from scr.ui.qt import QApplication
    from scr.ui.views.training import TrainPage

    project_model = tmp_path / "project" / "data" / "models" / "shared.pt"
    app_model_dir = tmp_path / "app" / "data" / "models"
    project_model.parent.mkdir(parents=True)
    app_model_dir.mkdir(parents=True)
    project_model.write_text("project", encoding="utf-8")
    (tmp_path / "project" / "data" / "models" / "project-only.pt").write_text("project", encoding="utf-8")
    (app_model_dir / "shared.pt").write_text("app", encoding="utf-8")
    (app_model_dir / "app-only.pt").write_text("app", encoding="utf-8")

    monkeypatch.setattr(training_service, "ROOT", tmp_path / "app")

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path / "project")
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
    )

    page = TrainPage(fake_app)
    items = [page.pretrained_combo.itemText(i) for i in range(page.pretrained_combo.count())]

    assert items == ["project-only.pt", "shared.pt", "app-only.pt"]
    assert page._resolve_model_reference("shared.pt") == str(project_model.resolve())


def test_train_page_unknown_model_defaults_to_project_models_dir(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication
    from scr.ui.views.training import TrainPage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
    )

    page = TrainPage(fake_app)

    assert page._resolve_model_reference("missing.pt") == str(
        (tmp_path / "data" / "models" / "missing.pt").resolve()
    )


def test_command_dialog_uses_wider_size():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.ui.dialogs import CommandDialog
    from scr.ui.qt import QApplication

    app = QApplication.instance() or QApplication([])
    dialog = CommandDialog(["pixi", "run", "yolo", "detect", "train"])

    assert dialog.minimumWidth() == 350
    assert dialog.minimumHeight() == 100
    assert dialog.width() == 700
    assert dialog.height() == 200


def test_training_page_persists_updated_fields_to_settings(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication
    from scr.ui.views.training import TrainPage

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


def test_train_page_starts_status_timer_only_when_visible(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication
    from scr.ui.views.training import TrainPage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
    )

    page = TrainPage(fake_app)

    assert page.train_status_timer.isActive() is False

    page.on_show()
    assert page.train_status_timer.isActive() is True

    page.on_hide()
    assert page.train_status_timer.isActive() is False


def test_train_page_stop_flow_recovers_buttons_and_hides_stop_noise(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication
    from scr.ui.views import training as training_view
    from scr.ui.views.training import TrainPage

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

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication
    from scr.ui.views import training as training_view
    from scr.ui.views.training import TrainPage

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
