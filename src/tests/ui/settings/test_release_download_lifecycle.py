import os

from types import SimpleNamespace


def test_release_download_progress_uses_requested_weights():
    from src.ui.features.settings.update_dialog import (
        _aggregate_download_percent,
        _download_percent,
        _download_weights,
    )

    assert _download_percent(0, 100) == 0
    assert _download_percent(0, 0) == 0
    assert _download_weights(False, 1) == (100,)
    assert _download_weights(True, 2) == (20, 80)
    assert _download_weights(True, 3) == (10, 45, 45)

    assert _aggregate_download_percent(0, 2, 100, 100, weights=(20, 80)) == 20
    assert _aggregate_download_percent(1, 2, 50, 100, weights=(20, 80)) == 60
    assert _aggregate_download_percent(0, 3, 100, 100, weights=(10, 45, 45)) == 10
    assert _aggregate_download_percent(1, 3, 100, 100, weights=(10, 45, 45)) == 55
    assert _aggregate_download_percent(2, 3, 100, 100, weights=(10, 45, 45)) == 100


def test_release_dialog_hot_installs_extra_environment_when_selected_alone(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.runtime.release_updates import ReleaseCheckResult
    from src.shared.qt import QApplication, QWidget
    from src.ui.features.settings.update_dialog import ReleaseUpdateDialog

    app = QApplication.instance() or QApplication([])
    host = QWidget()
    installed = []
    host.install_model_export_package = installed.append
    dialog = ReleaseUpdateDialog(
        host,
        ReleaseCheckResult(
            current_version="1.3.3",
            latest_version="1.4.0",
            environment_asset_names=("YOLOTool_ExtraEnv_v2.7z",),
            environment_asset_urls=("https://github.com/example/extra.7z",),
            update_available=True,
        ),
    )
    dialog.extra_environment_checkbox.setChecked(True)
    package_path = tmp_path / "YOLOTool_ExtraEnv_v2.7z"

    dialog._apply_download_result("release_assets_download", (package_path,))

    assert installed == [package_path]
    assert "热安装" in dialog.progress_message.text()
    dialog.close()
    host.close()



def test_release_dialog_uses_install_copy_for_extra_only_selection():
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
            environment_asset_names=("YOLOTool_ExtraEnv_v2.7z",),
            environment_asset_urls=("https://github.com/example/extra.7z",),
            update_available=True,
        ),
    )

    dialog.extra_environment_checkbox.setChecked(True)

    assert dialog.download_button.text() == "下载并安装所选资源"
    assert "自动安装" in dialog.progress_message.text()
    dialog.close()



def test_release_dialog_pauses_and_resumes_download():
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
            update_available=True,
        ),
    )
    dialog._worker = object()
    dialog.pause_button.setEnabled(True)

    dialog._toggle_pause()
    assert dialog._pause_event.is_set()
    assert dialog.pause_button.text() == "继续下载"
    assert dialog.progress_message.text() == "下载已暂停。"

    dialog._toggle_pause()
    assert not dialog._pause_event.is_set()
    assert dialog.pause_button.text() == "暂停下载"
    assert dialog.progress_message.text() == "正在继续下载…"
    dialog._worker = None
    dialog.close()



def test_release_dialog_stop_cancels_download():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.runtime.release_updates import ReleaseCheckResult
    from src.shared.qt import QApplication
    from src.ui.features.settings.update_dialog import ReleaseUpdateDialog

    app = QApplication.instance() or QApplication([])
    dialog = ReleaseUpdateDialog(
        None,
        ReleaseCheckResult(current_version="1.3.3", latest_version="1.4.0"),
    )
    dialog._worker = object()
    dialog.stop_button.setEnabled(True)

    dialog._stop_download()

    assert dialog._stop_event.is_set()
    assert dialog.stop_button.isEnabled() is False
    assert dialog.pause_button.isEnabled() is False
    assert dialog.progress_message.text() == "正在取消下载…"
    dialog._worker = None
    dialog.close()


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



def test_release_dialog_confirms_replacing_installed_extra_environment(monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from types import SimpleNamespace

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
            environment_asset_names=("YOLOTool_ExtraEnv_v2.7z",),
            environment_asset_urls=("https://github.com/example/extra.7z",),
            update_available=True,
        ),
    )
    dialog.extra_environment_checkbox.setChecked(True)
    monkeypatch.setattr(
        update_dialog,
        "load_installed_extension",
        lambda: SimpleNamespace(version="runtime-2"),
    )
    captured = []
    monkeypatch.setattr(
        update_dialog.QMessageBox,
        "question",
        lambda _parent, title, message, *_args: captured.append((title, message))
        or QMessageBox.StandardButton.No,
    )

    assert dialog._confirm_download_selection() is False
    assert captured == [
        (
            "重新下载附加包",
            "已经安装附加包，当前附加包为最新版本，是否重新下载并替换？",
        )
    ]
    dialog.close()



def test_release_dialog_distinguishes_extra_environment_with_program_selected(
    monkeypatch,
):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from types import SimpleNamespace

    from src.services.runtime.release_updates import ReleaseCheckResult
    from src.shared.qt import QApplication, QMessageBox
    from src.ui.features.settings import update_dialog
    from src.ui.features.settings.update_dialog import ReleaseUpdateDialog

    app = QApplication.instance() or QApplication([])
    result = ReleaseCheckResult(
        current_version="1.3.3",
        latest_version="1.4.0",
        installer_asset_name="YOLOTool_Setup_1.4.0.exe",
        installer_asset_url="https://github.com/example/setup.exe",
        environment_asset_names=("YOLOTool_ExtraEnv_v2.7z",),
        environment_asset_urls=("https://github.com/example/extra.7z",),
        update_available=True,
    )
    dialog = ReleaseUpdateDialog(None, result)
    dialog.extra_environment_checkbox.setChecked(True)
    monkeypatch.setattr(
        update_dialog,
        "load_installed_extension",
        lambda: SimpleNamespace(version="runtime-2"),
    )
    dialog._sync_pre_download_message()
    assert "下载后将替换" in dialog.progress_message.text()
    assert dialog.progress_message.property("warning") is True
    captured = []
    monkeypatch.setattr(
        update_dialog.QMessageBox,
        "question",
        lambda _parent, title, message, *_args: captured.append((title, message))
        or QMessageBox.StandardButton.No,
    )
    assert dialog._confirm_download_selection() is False
    assert captured[0][0] == "重新下载附加包"
    dialog.close()

    fresh_dialog = ReleaseUpdateDialog(None, result)
    fresh_dialog.extra_environment_checkbox.setChecked(True)
    monkeypatch.setattr(update_dialog, "load_installed_extension", lambda: None)
    fresh_dialog._sync_pre_download_message()
    assert "自动安装" in fresh_dialog.progress_message.text()
    assert fresh_dialog.progress_message.property("warning") is False
    fresh_dialog.close()



def test_release_dialog_distinguishes_all_three_selected_resources(monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.runtime.release_updates import ReleaseCheckResult
    from src.shared.qt import QApplication, QMessageBox
    from src.ui.features.settings import update_dialog
    from src.ui.features.settings.update_dialog import ReleaseUpdateDialog

    app = QApplication.instance() or QApplication([])
    result = ReleaseCheckResult(
        current_version="1.3.3",
        latest_version="1.4.0",
        installer_asset_name="YOLOTool_Setup_1.4.0.exe",
        installer_asset_url="https://github.com/example/setup.exe",
        environment_asset_names=(
            "YOLOTool_BaseEnv_v2.7z",
            "YOLOTool_ExtraEnv_v2.7z",
        ),
        environment_asset_urls=(
            "https://github.com/example/base.7z",
            "https://github.com/example/extra.7z",
        ),
        base_environment_update_available=False,
        extra_environment_update_available=False,
        update_available=True,
    )
    dialog = ReleaseUpdateDialog(None, result)
    dialog.extra_environment_checkbox.setChecked(True)
    dialog.base_environment_checkbox.setChecked(True)
    monkeypatch.setattr(update_dialog, "load_installed_extension", lambda: None)
    dialog._sync_pre_download_message()
    assert "重装基础环境包" in dialog.progress_message.text()
    assert "自动安装" in dialog.progress_message.text()
    assert dialog.progress_message.property("warning") is True
    dialog.close()

    installed_dialog = ReleaseUpdateDialog(None, result)
    installed_dialog.extra_environment_checkbox.setChecked(True)
    installed_dialog.base_environment_checkbox.setChecked(True)
    from types import SimpleNamespace

    monkeypatch.setattr(
        update_dialog,
        "load_installed_extension",
        lambda: SimpleNamespace(version="runtime-2"),
    )
    installed_dialog._sync_pre_download_message()
    assert "重装基础环境包" in installed_dialog.progress_message.text()
    assert "替换" in installed_dialog.progress_message.text()
    captured = []
    monkeypatch.setattr(
        update_dialog.QMessageBox,
        "warning",
        lambda _parent, title, message, *_args: captured.append((title, message))
        or QMessageBox.StandardButton.No,
    )
    assert installed_dialog._confirm_download_selection() is False
    assert captured[0][0] == "确认重新安装环境包"
    installed_dialog.close()



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



def test_release_dialog_hides_and_keeps_download_active_when_closed():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.runtime.release_updates import ReleaseCheckResult
    from src.shared.qt import QApplication
    from src.ui.features.settings.update_dialog import ReleaseUpdateDialog

    app = QApplication.instance() or QApplication([])
    dialog = ReleaseUpdateDialog(
        None,
        ReleaseCheckResult(current_version="1.3.3", latest_version="1.4.0"),
    )
    dialog._worker = object()

    dialog.show()
    dialog.reject()

    assert dialog.isVisible() is False
    dialog._worker = None
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
    assert checked_versions == ["1.3.3"]

