import os

from types import SimpleNamespace

def test_release_dialog_pauses_and_resumes_running_installer(monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.runtime.release_updates import ReleaseCheckResult
    from src.shared.qt import QApplication
    from src.ui.features.settings import update_dialog
    from src.ui.features.settings.update_dialog import ReleaseUpdateDialog

    app = QApplication.instance() or QApplication([])
    dialog = ReleaseUpdateDialog(
        None,
        ReleaseCheckResult(current_version="1.3.3", latest_version="1.4.0"),
    )
    process = object()
    calls = []
    monkeypatch.setattr(update_dialog, "pause_installer", lambda value: calls.append(("pause", value)))
    monkeypatch.setattr(update_dialog, "resume_installer", lambda value: calls.append(("resume", value)))
    dialog._installer_process = process
    dialog.pause_button.setEnabled(True)
    dialog.pause_button.setText("暂停安装")

    dialog._toggle_pause()
    assert dialog._installer_paused is True
    assert dialog.pause_button.text() == "继续安装"
    dialog._toggle_pause()
    assert dialog._installer_paused is False
    assert dialog.pause_button.text() == "暂停安装"
    assert calls == [("pause", process), ("resume", process)]
    dialog.close()

def test_release_dialog_reports_installer_launch_failure_without_sticking(
    monkeypatch, tmp_path
):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.runtime.release_updates import ReleaseCheckResult
    from src.shared.qt import QApplication
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
            update_available=True,
        ),
    )
    installer = tmp_path / "YOLOTool_Setup_1.4.0.exe"
    monkeypatch.setattr(
        update_dialog,
        "launch_installer",
        lambda _path: (_ for _ in ()).throw(OSError("无法启动")),
    )

    dialog._apply_download_result("release_assets_download", (installer,))

    assert dialog.progress_bar.value() == 100
    assert "安装包启动失败" in dialog.progress_message.text()
    assert dialog.download_button.isEnabled()
    dialog.close()

def test_settings_page_starts_release_check_when_shown(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src import APP_VERSION
    from src.services.runtime.release_updates import ReleaseCheckResult
    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.settings import state as settings_state
    from src.ui.features.settings.page import SettingsPage

    app = QApplication.instance() or QApplication([])
    started = []
    checked_versions = []
    monkeypatch.setattr(
        settings_state,
        "check_latest_release",
        lambda current_version=APP_VERSION: checked_versions.append(current_version)
        or ReleaseCheckResult(current_version=current_version),
    )
    fake_app = SimpleNamespace(
        settings=build_default_settings(tmp_path),
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda kind, fn, **_kwargs: (
            started.append(kind),
            fn() if kind == "release_check" else None,
        ),
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
        workers=[],
    )
    page = SettingsPage(fake_app)

    page.on_show()
    page.on_show()

    assert started == ["env", "release_check", "env"]
    assert checked_versions == ["1.3.4"]
