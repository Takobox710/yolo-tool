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


def test_settings_page_applies_dependency_payload_to_cards(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.settings.page import SettingsPage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
        workers=[],
    )

    page = SettingsPage(fake_app)
    page.apply_env(
        {
            "python": "3.12.10",
            "cuda": {"torch": "2.12.1+cu130", "cuda": "13.0", "gpu": "Test GPU"},
            "dependencies": {
                "ONNX": "1.22.0",
                "Ultralytics": "8.4.80",
                "OpenCV": "4.13.0",
                "Pillow": "12.2.0",
                "TensorRT": "11.1.0",
            },
            "app_version": "1.3.0",
        }
    )

    assert page.status_cards["Python"].text() == "3.12.10：可用"
    assert page.status_cards["Torch"].text() == "2.12.1+cu130：可用"
    assert page.status_cards["ONNX"].text() == "1.22.0：可用"
    assert page.status_cards["Ultralytics"].text() == "8.4.80：可用"
    assert page.status_cards["OpenCV"].text() == "4.13.0：可用"
    assert page.status_cards["Pillow"].text() == "12.2.0：可用"
    assert page.status_cards["TensorRT"].text() == "11.1.0：可用"
    assert list(page.status_cards) == [
        "Python",
        "Torch",
        "Ultralytics",
        "OpenCV",
        "Pillow",
        "ONNX",
        "TensorRT",
        "程序版本",
    ]
    assert page.status_cards["程序版本"].text() == "1.3.0"
    assert page.acceptDrops()


def test_settings_page_routes_dropped_model_export_archive_to_confirmation(
    monkeypatch, tmp_path
):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication, QEvent, QUrl
    from src.ui.features.settings.page import SettingsPage

    class DropEvent:
        def __init__(self, path):
            self.path = path
            self.accepted = False

        def type(self):
            return QEvent.Type.Drop

        def mimeData(self):
            return SimpleNamespace(
                hasUrls=lambda: True,
                urls=lambda: [QUrl.fromLocalFile(str(self.path))],
            )

        def acceptProposedAction(self):
            self.accepted = True

    app = QApplication.instance() or QApplication([])
    fake_app = SimpleNamespace(
        settings=build_default_settings(tmp_path),
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
        workers=[],
    )
    page = SettingsPage(fake_app)
    package = tmp_path / "runtime.7z"
    package.touch()
    selected = []
    monkeypatch.setattr(page, "confirm_model_export_package", selected.append)
    event = DropEvent(package)

    handled = page.eventFilter(page.log, event)

    assert handled is True
    assert event.accepted is True
    assert selected == [package]


def test_settings_toggle_refreshes_validation_page_model_choices(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.settings.page import SettingsPage
    from src.ui.features.validation.page import ValidatePage

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
