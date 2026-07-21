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


def test_settings_page_exposes_distribution_mode_before_custom_command(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication, QCheckBox
    from src.ui.features.settings.page import SettingsPage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
        pages={},
    )

    page = SettingsPage(fake_app)
    checks = [check.text().replace(" ⓘ", "") for check in page.findChildren(QCheckBox)]

    assert checks.index("多类别分布模式") < checks.index("训练前显示自定义命令框")
    assert "模型验证显示 last" in checks


def test_settings_page_adds_help_symbols_and_tooltips(tmp_path):
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
        pages={},
    )

    page = SettingsPage(fake_app)

    assert page.distribution_mode_check.text() == "多类别分布模式 ⓘ"
    assert page.distribution_mode_check.toolTip() == "开启后首页按多类别模式展示类别分布；顶部只显示总图片数，柱状图按各类别分别统计。"
    assert page.cmd_dialog_check.text() == "训练前显示自定义命令框 ⓘ"
    assert page.cmd_dialog_check.toolTip() == "开启后点击开始训练会先弹出自定义命令框；关闭后直接按当前配置启动训练。"
    assert page.help_icon_check.text() == "显示配置解释符号 ⓘ"
    assert page.help_icon_check.toolTip() == "开启后在配置名称后显示 ⓘ；关闭时只隐藏符号，鼠标悬停字段名称本身仍可查看解释。"
    assert page.show_last_models_check.text() == "模型验证显示 last ⓘ"
    assert page.show_last_models_check.toolTip() == "开启后模型验证页的模型列表会额外显示各训练目录下的 last.pt；关闭时只显示 best.pt。"


def test_settings_page_can_reset_defaults_with_confirmation(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication, QMessageBox
    from src.ui.features.settings.page import SettingsPage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    settings["features"]["custom_command_dialog"] = False
    settings["features"]["show_help_icons"] = False
    calls = {"count": 0}

    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
        reset_project_settings=lambda current_page=None: calls.update(
            {"count": calls["count"] + 1, "page": current_page}
        ),
    )

    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *_args, **_kwargs: QMessageBox.StandardButton.Yes,
    )

    page = SettingsPage(fake_app)
    page.reset_btn.click()

    assert calls["count"] == 1
    assert calls["page"] == "settings"


def test_settings_page_places_system_info_above_controls(tmp_path):
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
    )

    page = SettingsPage(fake_app)
    info_outer = page.layout().itemAt(1).widget()
    controls_row = page.layout().itemAt(2).widget()

    assert info_outer.objectName() == "systemInfoOuter"
    assert controls_row.layout().count() == 6


def test_settings_page_shows_program_log_title(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication, QLabel
    from src.ui.features.settings.page import SettingsPage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
    )

    page = SettingsPage(fake_app)
    labels = [label.text() for label in page.findChildren(QLabel)]

    assert "程序日志" in labels


def test_settings_page_uses_dependency_focused_status_cards(tmp_path):
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
    )

    page = SettingsPage(fake_app)

    assert list(page.status_cards.keys()) == [
        "Python",
        "Torch",
        "Ultralytics",
        "PySide6",
        "OpenCV",
        "Pillow",
        "psutil",
        "程序版本",
    ]


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
    )

    page = SettingsPage(fake_app)
    page.apply_env(
        {
            "python": "3.12.10",
            "cuda": {"torch": "2.12.1+cu130", "cuda": "13.0", "gpu": "Test GPU"},
            "dependencies": {
                "PySide6": "6.10.0",
                "Ultralytics": "8.4.80",
                "OpenCV": "4.13.0",
                "Pillow": "12.2.0",
                "psutil": "7.2.2",
            },
            "app_version": "1.2.5",
        }
    )

    assert page.status_cards["Python"].text() == "3.12.10：可用"
    assert page.status_cards["Torch"].text() == "2.12.1+cu130：可用"
    assert page.status_cards["PySide6"].text() == "6.10.0：可用"
    assert page.status_cards["Ultralytics"].text() == "8.4.80：可用"
    assert page.status_cards["OpenCV"].text() == "4.13.0：可用"
    assert page.status_cards["Pillow"].text() == "12.2.0：可用"
    assert page.status_cards["psutil"].text() == "7.2.2：可用"
    assert page.status_cards["程序版本"].text() == "1.2.5"


def test_settings_page_marks_torch_without_cuda_as_cuda_unavailable(tmp_path):
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
    )

    page = SettingsPage(fake_app)
    page.apply_env(
        {
            "python": "3.12.10",
            "cuda": {"torch": "2.12.1+cu130", "cuda": "未知", "gpu": "不可用"},
            "dependencies": {},
            "app_version": "1.2.5",
        }
    )

    assert page.status_cards["Torch"].text() == "2.12.1+cu130：CUDA不可用"


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


def test_settings_page_shows_program_log_instead_of_env_json(tmp_path):
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
        program_log_text=lambda: "[12:00:00] [INFO] 程序启动。",
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
    )

    page = SettingsPage(fake_app)
    page.on_show()
    page.apply_env(
        {
            "python": "3.12.10",
            "cuda": {"torch": "2.12.1+cu130", "cuda": "13.0"},
            "dependencies": {},
            "app_version": "1.2.5",
        }
    )

    assert page.log.toPlainText() == "[12:00:00] [INFO] 程序启动。"


def test_settings_page_can_append_program_log_entry(tmp_path):
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
        program_log_text=lambda: "等待程序日志...",
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
    )

    page = SettingsPage(fake_app)
    page.append_program_log_entry("[12:00:00] [ERROR] 检测失败")

    assert page.log.toPlainText() == "[12:00:00] [ERROR] 检测失败"


