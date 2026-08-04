import os

from types import SimpleNamespace

def test_release_update_dialog_manual_check_uses_background_task():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.runtime.release_updates import ReleaseCheckResult
    from src.shared.qt import QApplication, QWidget
    from src.ui.features.settings.update_dialog import ReleaseUpdateDialog

    app = QApplication.instance() or QApplication([])
    host = QWidget()
    calls = []
    host.context = SimpleNamespace(
        run_background=lambda *args, **kwargs: calls.append((args, kwargs))
    )
    result = ReleaseCheckResult(current_version="1.3.3")
    dialog = ReleaseUpdateDialog(host, result)

    dialog.refresh_button.click()

    assert calls[0][0][0] == "release_check"
    assert calls[0][1]["receiver"] is host
    assert dialog.refresh_button.isEnabled() is False
    dialog.apply_release_check_result(result)
    assert dialog.refresh_button.isEnabled() is True
    dialog.close()
    host.close()

def test_release_update_dialog_hides_environment_update_hint_for_equal_versions():
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
            environment_asset_names=(
                "YOLOTool_BaseEnv_v2.7z",
                "YOLOTool_ExtraEnv_v3.7z",
            ),
            environment_asset_urls=(
                "https://github.com/example/base.7z",
                "https://github.com/example/extra.7z",
            ),
            base_environment_version="2.0.0",
            extra_environment_version="2.0.0",
            installed_base_environment_version="2.0.0",
            installed_extra_environment_version="2.0.0",
            base_environment_update_available=False,
            extra_environment_update_available=False,
            update_available=True,
        ),
    )

    assert dialog.findChild(type(dialog.progress_message), "releaseEnvironmentTitle") is None
    assert dialog.program_checkbox.isChecked()
    assert dialog.base_environment_checkbox.isChecked() is False
    assert dialog.base_environment_checkbox.isEnabled()
    assert "检测到最新版本，点击按钮即可更新" in dialog.progress_message.text()
    assert dialog.progress_message.property("warning") is False
    dialog.base_environment_checkbox.setChecked(True)
    assert "版本与本机一致" in dialog.progress_message.text()
    assert "重装一次基础环境包" in dialog.progress_message.text()
    assert dialog.progress_message.property("warning") is True
    dialog.close()

def test_release_update_dialog_explains_missing_optional_extra_environment():
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
            environment_asset_names=("YOLOTool_ExtraEnv_v3.7z",),
            environment_asset_urls=("https://github.com/example/extra.7z",),
            extra_environment_version="2.0.0",
            installed_extra_environment_version="",
            extra_environment_update_available=False,
            update_available=True,
        ),
    )

    title = dialog.findChild(type(dialog.progress_message), "releaseEnvironmentTitle")
    text = dialog.findChild(type(dialog.progress_message), "releaseEnvironmentText")
    assert title is not None
    assert title.text() == "当前环境无附加包"
    assert text is not None
    assert text.text() == "可在本界面选择性下载安装附加环境包。"
    assert dialog.extra_environment_checkbox.isEnabled()
    assert dialog.extra_environment_checkbox.isChecked() is False
    dialog.close()

def test_release_update_dialog_hides_all_environment_notice_when_everything_matches():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.runtime.release_updates import ReleaseCheckResult
    from src.shared.qt import QApplication
    from src.ui.features.settings.update_dialog import ReleaseUpdateDialog

    app = QApplication.instance() or QApplication([])
    dialog = ReleaseUpdateDialog(
        None,
        ReleaseCheckResult(
            current_version="1.3.3",
            latest_version="1.3.3",
            installer_asset_name="YOLOTool_Setup_1.3.3.exe",
            installer_asset_url="https://github.com/example/setup.exe",
            environment_asset_names=(
                "YOLOTool_BaseEnv_v2.7z",
                "YOLOTool_ExtraEnv_v3.7z",
            ),
            environment_asset_urls=(
                "https://github.com/example/base.7z",
                "https://github.com/example/extra.7z",
            ),
            base_environment_version="2.0.0",
            extra_environment_version="2.0.0",
            installed_base_environment_version="2.0.0",
            installed_extra_environment_version="2.0.0",
            base_environment_update_available=False,
            extra_environment_update_available=False,
            update_available=False,
        ),
    )

    assert dialog.findChild(type(dialog.progress_message), "releaseEnvironmentNotice") is None
    dialog.close()

def test_release_update_dialog_shows_latest_message_when_nothing_needs_update(
    monkeypatch,
):
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
            latest_version="1.3.3",
            installer_asset_name="YOLOTool_Setup_1.3.3.exe",
            installer_asset_url="https://github.com/example/setup.exe",
            base_environment_version="2.0.0",
            installed_base_environment_version="2.0.0",
            base_environment_update_available=False,
            extra_environment_update_available=False,
            update_available=False,
        ),
    )

    assert dialog.progress_message.text() == "当前已是最新版本，无需更新。"
    assert dialog.progress_message.property("warning") is False
    monkeypatch.setattr(
        update_dialog.QMessageBox,
        "question",
        lambda *_args: QMessageBox.StandardButton.No,
    )
    assert dialog._confirm_download_selection() is False
    dialog.close()
