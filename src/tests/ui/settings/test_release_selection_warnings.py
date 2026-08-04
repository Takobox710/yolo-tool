import os

from types import SimpleNamespace

def test_release_dialog_warns_when_base_environment_has_no_program():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.runtime.release_updates import ReleaseCheckResult
    from src.shared.qt import QApplication
    from src.ui.features.settings.update_dialog import ReleaseUpdateDialog

    app = QApplication.instance() or QApplication([])
    dialog = ReleaseUpdateDialog(
        None,
        ReleaseCheckResult(
            current_version="1.3.3",
            latest_version="1.4.0",
            installer_asset_name="YOLOTool_Setup_1.4.0.exe",
            installer_asset_url="https://github.com/example/setup.exe",
            environment_asset_names=("YOLOTool_BaseEnv_v2.7z",),
            environment_asset_urls=("https://github.com/example/base.7z",),
            update_available=True,
        ),
    )

    dialog.base_environment_checkbox.setChecked(True)
    dialog.program_checkbox.setChecked(False)

    assert dialog.program_checkbox.isChecked() is False
    assert "没有程序无法安装" in dialog.progress_message.text()
    assert dialog.progress_message.property("warning") is True
    dialog.close()

def test_release_dialog_warns_before_program_only_update(monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.runtime.release_updates import ReleaseCheckResult
    from src.shared.qt import QApplication, QMessageBox
    from src.ui.features.settings import update_dialog
    from src.ui.features.settings.update_dialog import ReleaseUpdateDialog

    app = QApplication.instance() or QApplication([])
    dialog = ReleaseUpdateDialog(
        None,
        ReleaseCheckResult(
            current_version="1.3.3",
            latest_version="1.4.0",
            installer_asset_name="YOLOTool_Setup_1.4.0.exe",
            installer_asset_url="https://github.com/example/setup.exe",
            environment_asset_names=("YOLOTool_BaseEnv_v2.7z",),
            environment_asset_urls=("https://github.com/example/base.7z",),
            update_available=True,
        ),
    )
    dialog.base_environment_checkbox.setChecked(False)
    calls = []
    monkeypatch.setattr(
        update_dialog.QMessageBox,
        "warning",
        lambda *_args: calls.append(True) or QMessageBox.StandardButton.No,
    )

    assert dialog._confirm_download_selection() is False
    assert calls == [True]
    dialog.close()
