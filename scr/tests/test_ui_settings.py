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


def test_settings_page_exposes_distribution_mode_before_custom_command(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication, QCheckBox
    from scr.ui.views.settings import SettingsPage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
        pages={},
    )

    page = SettingsPage(fake_app)
    checks = [check.text() for check in page.findChildren(QCheckBox)]

    assert checks.index("多类别分布模式") < checks.index("训练前显示自定义命令框")


def test_settings_page_can_reset_defaults_with_confirmation(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication, QMessageBox
    from scr.ui.views.settings import SettingsPage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    settings["features"]["custom_command_dialog"] = False
    settings["features"]["show_help_icons"] = False
    calls = {"count": 0}

    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
        reset_project_settings=lambda current_page=None: calls.update(
            {"count": calls["count"] + 1, "page": current_page}
        ),
    )

    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *_args, **_kwargs: QMessageBox.StandardButton.Yes,
    )

    page = SettingsPage(fake_app)
    page.reset_btn.click()

    assert calls["count"] == 1
    assert calls["page"] == "settings"


def test_settings_page_places_system_info_above_controls(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication
    from scr.ui.views.settings import SettingsPage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
    )

    page = SettingsPage(fake_app)
    info_outer = page.layout().itemAt(1).widget()
    controls_row = page.layout().itemAt(2).widget()

    assert info_outer.objectName() == "systemInfoOuter"
    assert controls_row.layout().count() == 6


def test_settings_toggle_refreshes_validation_page_model_choices(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication
    from scr.ui.views.settings import SettingsPage
    from scr.ui.views.validation import ValidatePage

    run_dir = tmp_path / "result" / "train-5" / "weights"
    run_dir.mkdir(parents=True)
    (run_dir / "best.pt").write_text("best", encoding="utf-8")
    (run_dir / "last.pt").write_text("last", encoding="utf-8")

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    settings["features"]["show_last_training_models"] = True
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
        pages={},
    )

    validate_page = ValidatePage(fake_app)
    validate_page.on_show()
    settings_page = SettingsPage(fake_app)
    fake_app.pages = {"validate": validate_page}

    before = [validate_page.model_combo.itemText(i) for i in range(validate_page.model_combo.count())]
    assert "train-5\\last.pt" in before

    settings_page.show_last_models_check.setChecked(False)

    after = [validate_page.model_combo.itemText(i) for i in range(validate_page.model_combo.count())]
    assert fake_app.settings["features"]["show_last_training_models"] is False
    assert "train-5\\last.pt" not in after
    assert "train-5\\best.pt" in after
