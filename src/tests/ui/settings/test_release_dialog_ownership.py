import os

from types import SimpleNamespace

def test_settings_page_version_value_opens_update_dialog(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.settings.page import SettingsPage

    app = QApplication.instance() or QApplication([])
    fake_app = SimpleNamespace(
        settings=build_default_settings(tmp_path),
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda *_args, **_kwargs: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
        workers=[],
    )
    page = SettingsPage(fake_app)
    clicked = []
    page.status_cards["程序版本"].clicked.disconnect()
    page.status_cards["程序版本"].clicked.connect(lambda: clicked.append(True))

    page.status_cards["程序版本"].clicked.emit()

    assert clicked == [True]
    page.close()

def test_release_update_dialog_is_owned_by_workbench_window(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication, QMainWindow, Qt
    from src.ui.features.settings.page import SettingsPage

    app = QApplication.instance() or QApplication([])
    host = QMainWindow()
    fake_app = SimpleNamespace(
        settings=build_default_settings(tmp_path),
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda *_args, **_kwargs: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
        workers=[],
    )
    page = SettingsPage(fake_app)
    host.setCentralWidget(page)
    page.open_release_update_dialog()

    dialog = page.release_update_dialog
    assert dialog is not None
    assert dialog.parentWidget() is host
    assert dialog.testAttribute(Qt.WidgetAttribute.WA_StyledBackground)

    dialog.close()
    host.close()


def test_release_update_option_visibility_never_uses_a_top_level_checkbox(monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.runtime.release_updates import ReleaseCheckResult
    from src.shared.qt import QApplication, QCheckBox, QMainWindow
    from src.ui.features.settings import update_dialog_layout
    from src.ui.features.settings.update_dialog import ReleaseUpdateDialog

    app = QApplication.instance() or QApplication([])
    visible_parent_widgets = []

    class TrackingCheckBox(QCheckBox):
        def setVisible(self, visible):  # noqa: N802 - Qt API name
            if visible:
                visible_parent_widgets.append(self.parentWidget())
            super().setVisible(visible)

    monkeypatch.setattr(update_dialog_layout, "QCheckBox", TrackingCheckBox)
    host = QMainWindow()
    dialog = ReleaseUpdateDialog(host, ReleaseCheckResult(current_version="1.3.4"))

    assert visible_parent_widgets
    assert all(parent is dialog for parent in visible_parent_widgets)

    dialog.close()
    host.close()
