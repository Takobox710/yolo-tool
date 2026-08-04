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

def test_release_dialog_selects_all_base_environment_volumes():
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
                "YOLOTool_BaseEnv_v3.7z.001",
                "YOLOTool_BaseEnv_v3.7z.002",
            ),
            environment_asset_urls=(
                "https://github.com/example/base.001",
                "https://github.com/example/base.002",
            ),
            base_environment_update_available=True,
            update_available=True,
        ),
    )
    dialog.base_environment_checkbox.setChecked(True)

    assert dialog._selected_assets() == (
        ("YOLOTool_Setup_1.4.0.exe", "https://github.com/example/setup.exe"),
        ("YOLOTool_BaseEnv_v3.7z.001", "https://github.com/example/base.001"),
        ("YOLOTool_BaseEnv_v3.7z.002", "https://github.com/example/base.002"),
    )
    dialog.close()

def test_cpu_release_dialog_only_offers_cpu_setup():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.runtime.release_updates import ReleaseCheckResult
    from src.shared.qt import QApplication
    from src.ui.features.settings.update_dialog import ReleaseUpdateDialog

    app = QApplication.instance() or QApplication([])
    dialog = ReleaseUpdateDialog(
        None,
        ReleaseCheckResult(
            current_version="1.3.3",
            variant="cpu",
            latest_version="1.4.0",
            installer_asset_name="YOLOTool_CPU_Setup_1.4.0.exe",
            installer_asset_url="https://github.com/example/cpu.exe",
            environment_asset_names=("YOLOTool_CPU_BaseEnv_v3.7z",),
            environment_asset_urls=("https://github.com/example/cpu-base.7z",),
            update_available=True,
        ),
    )

    assert dialog.program_checkbox.isChecked() is True
    assert dialog.base_environment_checkbox.isVisible() is False
    assert dialog.extra_environment_checkbox.isVisible() is False
    assert dialog._selected_assets() == (
        ("YOLOTool_CPU_Setup_1.4.0.exe", "https://github.com/example/cpu.exe"),
    )
    dialog.close()

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
            environment_asset_names=("YOLOTool_ExtraEnv_v3.7z",),
            environment_asset_urls=("https://github.com/example/extra.7z",),
            update_available=True,
        ),
    )
    dialog.extra_environment_checkbox.setChecked(True)
    package_path = tmp_path / "YOLOTool_ExtraEnv_v3.7z"

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
            environment_asset_names=("YOLOTool_ExtraEnv_v3.7z",),
            environment_asset_urls=("https://github.com/example/extra.7z",),
            update_available=True,
        ),
    )

    dialog.extra_environment_checkbox.setChecked(True)

    assert dialog.download_button.text() == "下载并安装所选资源"
    assert "自动安装" in dialog.progress_message.text()
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
            environment_asset_names=("YOLOTool_ExtraEnv_v3.7z",),
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
        environment_asset_names=("YOLOTool_ExtraEnv_v3.7z",),
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
            "YOLOTool_ExtraEnv_v3.7z",
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
