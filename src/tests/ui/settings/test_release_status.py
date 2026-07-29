import os

from types import SimpleNamespace


def test_settings_page_shows_upgrade_indicator_for_new_release(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.runtime.release_updates import ReleaseCheckResult
    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication, Qt
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

    page.apply_release_check(
        ReleaseCheckResult(
            current_version="1.2.9",
            latest_version="1.3.0",
            release_url="https://github.com/Takobox710/yolo-tool/releases/tag/v1.3.0",
            release_notes="- 修复系统设置模块环境显示错位。\n\x1b[36m- 优化更新弹窗动画。\x1b[0m",
            update_available=True,
        )
    )

    assert page.upgrade_indicator.isHidden() is False
    assert page.upgrade_indicator.size().width() == 26
    assert page.upgrade_indicator.iconSize().width() == 18
    assert page.upgrade_indicator.cursor().shape() == Qt.CursorShape.PointingHandCursor
    assert page.upgrade_indicator.icon().isNull() is False
    assert "1.3.0" in page.upgrade_indicator.toolTip()
    assert page.release_check_toast.isHidden() is False
    assert "发现新版本" in page.release_check_toast.message.text()
    assert "1.3.0 更新内容：" in page.log.toPlainText()
    assert "环境显示错位" in page.log.toPlainText()
    assert "\x1b" not in page.log.toPlainText()
    page.apply_release_check(
        ReleaseCheckResult(
            current_version="1.2.9",
            latest_version="1.3.0",
            release_notes="- 修复系统设置模块环境显示错位。\n\x1b[36m- 优化更新弹窗动画。\x1b[0m",
            update_available=True,
        )
    )
    assert page.log.toPlainText().count("1.3.0 更新内容：") == 1
    assert page.release_check_toast._entrance_animation.duration() == 180
    assert page.release_check_toast._progress_animation.duration() == 4200



def test_settings_page_hides_upgrade_indicator_when_current(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.runtime.release_updates import ReleaseCheckResult
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

    page.apply_release_check(
        ReleaseCheckResult(current_version="1.3.0", latest_version="1.3.0")
    )

    assert page.upgrade_indicator.isVisible() is False
    assert page.release_check_toast.isHidden() is False
    assert page.release_check_toast.message.text() == "当前已是最新版本。"



def test_release_update_dialog_shows_version_progress_and_environment_hint(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.runtime.release_updates import ReleaseCheckResult
    from src.shared.qt import QApplication
    from src.ui.features.settings.update_dialog import ReleaseUpdateDialog

    app = QApplication.instance() or QApplication([])
    dialog = ReleaseUpdateDialog(
        None,
        ReleaseCheckResult(
            current_version="1.2.9",
            latest_version="1.3.0",
            release_url="https://github.com/example/release",
            release_notes="- 修复环境显示\n- 优化更新流程",
            installer_asset_name="YOLOTool_Setup_1.3.0.exe",
            installer_asset_url="https://github.com/example/setup.exe",
            environment_asset_names=("YOLOTool_BaseEnv_v2.7z",),
            environment_asset_urls=("https://github.com/example/base.7z",),
            update_available=True,
        ),
    )

    assert dialog.windowTitle() == "GitHub Release 更新"
    assert dialog.notes.toPlainText().startswith("- 修复环境显示")
    assert dialog.progress_bar.value() == 0
    assert dialog.download_button.isEnabled()
    assert dialog.github_button.isEnabled()
    assert dialog.program_checkbox.isChecked()
    assert dialog.program_checkbox.isEnabled()
    assert dialog.base_environment_checkbox.isChecked() is True
    assert dialog.base_environment_checkbox.isEnabled()
    assert dialog.extra_environment_checkbox.isEnabled() is False
    assert "一起下载" in dialog.progress_message.text()
    assert dialog.progress_message.property("warning") is False
    assert dialog.findChild(type(dialog.progress_message), "releaseEnvironmentTitle")
    assert dialog.findChild(type(dialog.progress_message), "releaseMetricValue").text() == "1.3.0"
    dialog.close()



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
                "YOLOTool_ExtraEnv_v2.7z",
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
            environment_asset_names=("YOLOTool_ExtraEnv_v2.7z",),
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
                "YOLOTool_ExtraEnv_v2.7z",
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



