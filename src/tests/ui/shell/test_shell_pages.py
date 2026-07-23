from pathlib import Path

import os

import subprocess

import sys

from types import SimpleNamespace

from src.tests.helpers.ui_paths import (
    APP,
    DATA_VIEW,
    FORMS,
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
    TRAIN_FORM_VIEW,
    TRAIN_VIEW,
    UI_BUNDLE_PATHS,
    VALIDATE_VIEW,
    WINDOW,
)


def _read_app():
    return APP.read_text(encoding="utf-8")

def _read_ui_bundle():
    return "\n".join(path.read_text(encoding="utf-8") for path in UI_BUNDLE_PATHS)


def test_workbench_window_lazy_loads_pages():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.shared.qt import QApplication
    from src.ui.shell.window import WorkbenchWindow

    app = QApplication.instance() or QApplication([])
    window = WorkbenchWindow()

    assert list(window.pages.keys()) == ["home"]
    assert window.stack.count() == 1


def test_workbench_window_switches_to_project_local_settings(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    import json

    from src.shared.qt import QApplication
    from src.ui.shell.window import WorkbenchWindow

    project_root = tmp_path / "project-b"
    settings_path = project_root / "data" / "runtime" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps({"training": {"epochs": 77}}, ensure_ascii=False),
        encoding="utf-8",
    )

    app = QApplication.instance() or QApplication([])
    window = WorkbenchWindow()

    window.switch_project_root(project_root)

    assert window.settings_service.settings_path == settings_path
    assert window.settings["project"]["root"] == str(project_root)
    assert window.settings["training"]["epochs"] == 77
    persisted = json.loads(settings_path.read_text(encoding="utf-8"))
    assert persisted["project"]["root"] == "."
    assert list(window.pages.keys()) == ["home"]


def test_data_page_expands_after_window_grows_from_initial_size():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.shared.qt import QApplication
    from src.ui.shell.window import WorkbenchWindow

    app = QApplication.instance() or QApplication([])
    window = WorkbenchWindow()
    try:
        window.show()
        app.processEvents()
        window.show_page("data")
        app.processEvents()

        window.resize(1800, 1000)
        app.processEvents()

        page = window.pages["data"]
        assert page.inner_page.width() == page.viewport().width()
        assert page.inner_page.minimumWidth() == page.viewport().width()
    finally:
        window.hide()
        window.deleteLater()
        app.processEvents()


def test_workbench_window_close_event_prompts_for_unsaved_annotations(monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtGui import QCloseEvent
    from src.shared.qt import QApplication, QMessageBox
    from src.ui.shell.window import WorkbenchWindow

    app = QApplication.instance() or QApplication([])
    window = WorkbenchWindow()
    annotation_widget = window.ensure_page("annotation")
    annotation_page = getattr(annotation_widget, "inner_page", annotation_widget)
    annotation_page.dirty = True
    asked = {"text": ""}
    save_calls = {"count": 0}

    def fake_question(_parent, _title, text, *_args, **_kwargs):
        asked["text"] = text
        return QMessageBox.StandardButton.No

    monkeypatch.setattr(QMessageBox, "question", fake_question)
    monkeypatch.setattr(window.settings_service, "save", lambda _data: save_calls.__setitem__("count", save_calls["count"] + 1))
    monkeypatch.setattr("src.ui.shell.window.stop_process", lambda _handle: None)

    event = QCloseEvent()
    window.closeEvent(event)

    assert event.isAccepted() is False
    assert save_calls["count"] == 0
    assert "当前有未保存的标注" in asked["text"]
