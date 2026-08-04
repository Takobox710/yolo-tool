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

def test_settings_page_refreshes_open_release_dialog(tmp_path):
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
    received = []
    page.release_update_dialog = SimpleNamespace(
        apply_release_check_result=received.append
    )
    result = ReleaseCheckResult(
        current_version="1.3.3",
        latest_version="1.4.0",
        update_available=True,
    )

    page.apply_release_check(result)

    assert received == [result]
    page.release_update_dialog = None
    page.close()

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
    assert dialog.download_speed_label.text() == "下载速度：0 B/s"
    assert dialog.download_size_label.text() == "已下载：0 B / --"
    assert dialog._download_speed_timer.interval() == 1000
    assert dialog.stop_button.isEnabled() is False
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
    dialog._apply_download_detail({"downloaded": 1048576, "total": 2097152})
    assert dialog.download_size_label.text() == "已下载：1.0 MB / 2.0 MB"
    dialog.close()

def test_release_update_dialog_refreshes_after_background_result():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.runtime.release_updates import ReleaseCheckResult
    from src.shared.qt import QApplication
    from src.ui.features.settings.update_dialog import ReleaseUpdateDialog

    app = QApplication.instance() or QApplication([])
    dialog = ReleaseUpdateDialog(
        None,
        ReleaseCheckResult(current_version="1.3.3"),
    )
    assert dialog.latest_version_label.text() == "-"
    assert dialog.program_checkbox.isEnabled() is False

    dialog.apply_release_check_result(
        ReleaseCheckResult(
            current_version="1.3.3",
            latest_version="1.4.0",
            release_notes="- 修复更新检测时序。",
            installer_asset_name="YOLOTool_Setup_1.4.0.exe",
            installer_asset_url="https://github.com/example/setup.exe",
            environment_asset_names=("YOLOTool_BaseEnv_v3.7z",),
            environment_asset_urls=("https://github.com/example/base.7z",),
            base_environment_update_available=True,
            update_available=True,
        )
    )

    assert dialog.latest_version_label.text() == "1.4.0"
    assert "更新检测时序" in dialog.notes.toPlainText()
    assert dialog.program_checkbox.isChecked()
    assert dialog.base_environment_checkbox.isChecked()
    assert dialog.findChild(type(dialog.progress_message), "releaseEnvironmentTitle")
    dialog.close()
