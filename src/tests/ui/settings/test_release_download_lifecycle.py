import os

from types import SimpleNamespace

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
