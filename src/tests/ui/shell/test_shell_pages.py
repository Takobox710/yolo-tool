from pathlib import Path

import os

import subprocess

import sys

from types import SimpleNamespace

from src.tests.helpers.ui_paths import (
    APP,
    DATA_VIEW,
    FORMS,
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
    TRAIN_FORM_VIEW,
    TRAIN_VIEW,
    UI_BUNDLE_PATHS,
    VALIDATE_VIEW,
    WINDOW,
)


def _read_app():
    return APP.read_text(encoding="utf-8")

def _read_ui_bundle():
    return "\n".join(path.read_text(encoding="utf-8") for path in UI_BUNDLE_PATHS)


def test_ui_modules_are_split_by_window_and_navigation_pages():
    app_src = _read_app()
    assert WINDOW.exists()
    assert PAGE_BASE.exists()
    assert HOME_VIEW.exists()
    assert DATA_VIEW.exists()
    assert TRAIN_FORM_VIEW.exists()
    assert TRAIN_VIEW.exists()
    assert VALIDATE_VIEW.exists()
    assert SETTINGS_VIEW.exists()
    assert "from src.ui.shell.window import WorkbenchWindow, build_style" in app_src
    assert "from src.ui.features.home.page import HomePage" not in app_src
    assert "class WorkbenchWindow" not in app_src
    assert "class HomePage" not in app_src
    assert "class DataPage" not in app_src
    assert "class TrainPage" not in app_src
    assert "class ValidatePage" not in app_src
    assert "class SettingsPage" not in app_src
    assert APP.stat().st_size < 12000


def test_base_page_status_text_uses_qmainwindow_status_bar(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.ui.shared.page_base import BasePage
    from src.shared.qt import QApplication, QMainWindow

    app = QApplication.instance() or QApplication([])
    window = QMainWindow()
    window.settings = build_default_settings(tmp_path)
    window.settings_service = SimpleNamespace(save=lambda _data: None)

    page = BasePage(window)
    page.set_status_text("检测中")

    assert window.statusBar().currentMessage() == "检测中"


def test_home_page_can_be_constructed_and_refreshed(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    import json

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication, QSizePolicy
    from src.ui.features.home.page import HomePage

    images_dir = tmp_path / "images"
    labels_dir = tmp_path / "labels"
    images_dir.mkdir()
    labels_dir.mkdir()
    from PIL import Image

    Image.new("RGB", (32, 32), "white").save(images_dir / "1.jpg")
    Image.new("RGB", (32, 32), "white").save(images_dir / "2.jpg")
    (images_dir / "1.json").write_text(
        json.dumps({"shapes": [{"label": "weld"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (images_dir / "2.json").write_text(
        json.dumps({"shapes": []}, ensure_ascii=False), encoding="utf-8"
    )
    (labels_dir / "1.txt").write_text("0 0.5 0.5 0.2 0.2\n0 0.4 0.4 0.1 0.1\n", encoding="utf-8")

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )

    page = HomePage(fake_app)
    page.on_show()
    margins = page.layout().contentsMargins()

    assert page.overview_stats["project"].toolTip() == str(tmp_path)
    assert page.overview_stats["image_count"].toolTip() == "2"
    assert page.overview_stats["label_count"].toolTip() == "1"
    assert page.minimumHeight() == 650
    assert margins.left() == 16
    assert margins.top() == 16
    assert margins.right() == 16
    assert margins.bottom() == 4
    assert all(
        card.sizePolicy().verticalPolicy() == QSizePolicy.Policy.Preferred
        for card in page._home_left_cards + page._home_right_cards
    )


def test_home_page_keeps_previous_counts_while_refreshing(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.home.page import HomePage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
    )

    page = HomePage(fake_app)
    page._set_overview_stat("image_count", "12")
    page._set_overview_stat("label_count", "7")

    page.on_show()

    assert page.overview_stats["image_count"].text() == "12"
    assert page.overview_stats["label_count"].text() == "7"
    assert page.overview_stats["image_count"].toolTip() == "12"
    assert page.overview_stats["label_count"].toolTip() == "7"


def test_main_pages_can_be_constructed(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.data.page import DataPage
    from src.ui.features.settings.page import SettingsPage
    from src.ui.features.training.page import TrainPage
    from src.ui.features.validation.page import ValidatePage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
    )

    data_page = DataPage(fake_app)
    train_page = TrainPage(fake_app)
    validate_page = ValidatePage(fake_app)
    settings_page = SettingsPage(fake_app)

    assert data_page.tool_stack.count() == 4
    assert train_page.start_btn.text() == "开始训练"
    assert validate_page.start_det_btn.text() == "开始检测"
    assert "Torch" in settings_page.status_cards
    assert settings_page.help_icon_check.isChecked() is True


def test_workbench_window_lazy_loads_pages():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.shared.qt import QApplication
    from src.ui.shell.window import WorkbenchWindow

    app = QApplication.instance() or QApplication([])
    window = WorkbenchWindow()

    assert list(window.pages.keys()) == ["home"]
    assert window.stack.count() == 1


def test_workbench_window_creates_pages_on_demand():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.shared.qt import QApplication
    from src.ui.shell.window import WorkbenchWindow

    app = QApplication.instance() or QApplication([])
    window = WorkbenchWindow()

    window.show_page("annotation")
    window.show_page("train")

    assert list(window.pages.keys()) == ["home", "annotation", "train"]
    assert window.stack.count() == 3


def test_workbench_window_warms_remaining_pages_after_show(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PIL import Image
    from src.shared.qt import QApplication
    from src.ui.shell.window import WorkbenchWindow

    app = QApplication.instance() or QApplication([])
    project_root = tmp_path / "project-warmup"
    images_dir = project_root / "images"
    images_dir.mkdir(parents=True)
    Image.new("RGB", (32, 32), "white").save(images_dir / "1.jpg")
    window = WorkbenchWindow()
    window.switch_project_root(project_root)
    window.show()
    for _ in range(8):
        app.processEvents()

    assert list(window.pages.keys()) == ["home", "annotation", "data", "train", "validate", "settings"]
    assert window.stack.count() == 6
    annotation_widget = window.pages["annotation"]
    annotation_page = getattr(annotation_widget, "inner_page", annotation_widget)
    assert len(annotation_page.image_items) == 1
    assert annotation_page.current_index == 0
    assert annotation_page.current_image_path == images_dir / "1.jpg"


def test_workbench_window_switches_to_project_local_settings(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    import json

    from src.shared.qt import QApplication
    from src.ui.shell.window import WorkbenchWindow

    project_root = tmp_path / "project-b"
    settings_path = project_root / "data" / "runtime" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps({"training": {"epochs": 77}}, ensure_ascii=False),
        encoding="utf-8",
    )

    app = QApplication.instance() or QApplication([])
    window = WorkbenchWindow()

    window.switch_project_root(project_root)

    assert window.settings_service.settings_path == settings_path
    assert window.settings["project"]["root"] == str(project_root)
    assert window.settings["training"]["epochs"] == 77
    persisted = json.loads(settings_path.read_text(encoding="utf-8"))
    assert persisted["project"]["root"] == "."
    assert list(window.pages.keys()) == ["home"]


def test_workbench_window_can_reset_current_project_settings(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    import json

    from src.shared.qt import QApplication, QMessageBox
    from src.ui.shell.window import WorkbenchWindow

    project_root = tmp_path / "project-reset"
    settings_path = project_root / "data" / "runtime" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps(
            {
                "training": {"epochs": 12},
                "rename": {"prefix": "custom"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    app = QApplication.instance() or QApplication([])
    window = WorkbenchWindow()
    window.switch_project_root(project_root)
    monkeypatch.setattr(QMessageBox, "information", lambda *_args, **_kwargs: None)

    window.reset_project_settings("settings")

    assert window.settings["project"]["root"] == str(project_root)
    assert window.settings["training"]["epochs"] == 500
    assert window.settings["training"]["patience"] == 100
    assert window.settings["training"]["base_model"] == "yolov8s.pt"
    assert window.settings["task"]["mode"] == "detect"
    assert window.settings["rename"]["prefix"] == "A"
    assert json.loads(settings_path.read_text(encoding="utf-8"))["training"]["epochs"] == 500
    assert window.current_page_key == "settings"


def test_workbench_window_restores_last_selected_project_root_on_restart(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    import json

    from src.services.settings import project_settings as settings_service
    from src.shared.qt import QApplication
    from src.ui.shell.window import WorkbenchWindow

    project_root = tmp_path / "project-c"
    settings_path = project_root / "data" / "runtime" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps({"training": {"epochs": 66}}, ensure_ascii=False),
        encoding="utf-8",
    )

    app_state_path = tmp_path / "app_state.json"
    monkeypatch.setattr(settings_service, "APP_STATE_PATH", app_state_path)

    qt_app = QApplication.instance() or QApplication([])
    first_window = WorkbenchWindow()
    first_window.switch_project_root(project_root)

    second_window = WorkbenchWindow()

    assert second_window.settings_service.settings_path == settings_path
    assert second_window.settings["project"]["root"] == str(project_root)
    assert second_window.settings["training"]["epochs"] == 66
    assert json.loads(app_state_path.read_text(encoding="utf-8"))["last_project_root"] == str(project_root.resolve())


def test_scheme_b_uses_label_tooltips_instead_of_help_icon():
    src = PAGE_BASE.read_text(encoding="utf-8") + FORMS.read_text(encoding="utf-8")
    assert "class HelpIcon" not in src
    assert "ⓘ" in src


def test_pages_add_placeholders_and_help_icons(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication, QCheckBox, QLabel
    from src.ui.features.data.convert.tab import ConvertTab
    from src.ui.features.data.preview.tab import PreviewTab
    from src.ui.features.data.rename.tab import RenameTab
    from src.ui.features.data.resize.tab import ResizeTab
    from src.ui.features.settings.page import SettingsPage
    from src.ui.features.training.page import TrainPage
    from src.ui.features.validation.page import ValidatePage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
        refresh_help_icon_visibility=lambda: None,
    )

    train_page = TrainPage(fake_app)
    convert_page = ConvertTab(fake_app)
    preview_page = PreviewTab(fake_app)
    rename_page = RenameTab(fake_app)
    resize_page = ResizeTab(fake_app)
    validate_page = ValidatePage(fake_app)
    settings_page = SettingsPage(fake_app)

    assert train_page.edits["lr"].placeholderText() == "例如 0.001"
    assert train_page.edits["epochs"].placeholderText() == "例如 300"
    assert convert_page.images_edit.placeholderText() == "选择待转换的图片目录"
    assert preview_page.image_edit.placeholderText() == "选择待预览的图片目录"
    assert rename_page.prefix_edit.placeholderText() == "例如 A"
    assert resize_page.canvas_edit.placeholderText() == "例如 960"
    assert validate_page.conf_edit.placeholderText() == "例如 0.25"
    assert int(convert_page.log.focusPolicy()) == int(convert_page.log.focusPolicy().NoFocus)
    assert int(resize_page.log.focusPolicy()) == int(resize_page.log.focusPolicy().NoFocus)
    assert int(validate_page.val_log.focusPolicy()) == int(validate_page.val_log.focusPolicy().NoFocus)
    assert int(settings_page.log.focusPolicy()) == int(settings_page.log.focusPolicy().NoFocus)
    assert int(train_page.log.focusPolicy()) == int(train_page.log.focusPolicy().NoFocus)
    train_labels = [label for label in train_page.findChildren(QLabel) if "ⓘ" in label.text()]
    train_checks = [check for check in train_page.findChildren(QCheckBox) if "ⓘ" in check.text()]
    convert_labels = [label for label in convert_page.findChildren(QLabel) if "ⓘ" in label.text()]
    preview_labels = [label for label in preview_page.findChildren(QLabel) if "ⓘ" in label.text()]
    rename_labels = [label for label in rename_page.findChildren(QLabel) if "ⓘ" in label.text()]
    resize_labels = [label for label in resize_page.findChildren(QLabel) if "ⓘ" in label.text()]
    validate_labels = [label for label in validate_page.findChildren(QLabel) if "ⓘ" in label.text()]
    settings_labels = [label for label in settings_page.findChildren(QLabel) if "ⓘ" in label.text()]
    settings_checks = [check for check in settings_page.findChildren(QCheckBox) if "ⓘ" in check.text()]
    assert len(train_labels) == 8
    assert len(train_checks) == 8
    assert len(convert_labels) == 6
    assert len(preview_labels) == 0
    assert len(rename_labels) == 0
    assert len(resize_labels) == 0
    assert len(validate_labels) == 0
    assert len(settings_labels) == 0
    assert len(settings_checks) == 4
    assert any(check.text() == "多类别分布模式 ⓘ" and check.toolTip() == "开启后首页按多类别模式展示类别分布；顶部只显示总图片数，柱状图按各类别分别统计。" for check in settings_checks)
    assert any(check.text() == "训练前显示自定义命令框 ⓘ" and check.toolTip() == "开启后点击开始训练会先弹出自定义命令框；关闭后直接按当前配置启动训练。" for check in settings_checks)
    assert any(check.text() == "显示配置解释符号 ⓘ" and check.toolTip() == "开启后在配置名称后显示 ⓘ；关闭时只隐藏符号，鼠标悬停字段名称本身仍可查看解释。" for check in settings_checks)
    assert any(check.text() == "模型验证显示 last ⓘ" and check.toolTip() == "开启后模型验证页的模型列表会额外显示各训练目录下的 last.pt；关闭时只显示 best.pt。" for check in settings_checks)
    assert any(label.text() == "训练轮数 ⓘ" and label.toolTip() == "训练轮数（epochs）；设置完整训练的总轮次，更大通常效果更好，但训练耗时更长。" for label in train_labels)
    assert any(label.text() == "线程数 ⓘ" and label.toolTip() == "数据加载线程数（workers）；提高后通常更快，但会占用更多 CPU 和系统内存。" for label in train_labels)
    assert any(label.text() == "图片尺寸 ⓘ" and label.toolTip() == "训练输入尺寸（imgsz）；更大可能更准，但更吃显存，也会占用更多系统内存和时间。" for label in train_labels)
    assert any(label.text() == "优化器 ⓘ" and label.toolTip() == "训练优化器（optimizer）；用于控制参数更新方式，auto 会交给 Ultralytics 自动决定。" for label in train_labels)
    assert any(label.text() == "设备 ⓘ" and label.toolTip() == "训练设备（device）；0 表示首张 GPU，cpu 表示使用处理器，也可填写多个 GPU 编号。" for label in train_labels)
    assert any(check.text() == "随机拼图 ⓘ" and check.toolTip() == "随机拼图增强（mosaic）；将多张图随机拼接成一张，增强小目标和复杂场景鲁棒性。" for check in train_checks)
    assert convert_page.labelme_check.text() == "Labelme 转 YOLO ⓘ"
    assert convert_page.labelme_check.toolTip() == "开启时自动识别 Labelme 类别并转换为 YOLO；关闭时只对已有 YOLO txt 标注重新分组。"
    assert convert_page.class_mapping_btn.text() == "自定义类别名称"
    assert convert_page.backup_yolo_check.text() == "备份标注文件 ⓘ"
    assert "data/old" in convert_page.backup_yolo_check.toolTip()
    assert convert_page.task_combo.itemText(0) == "detect"
    assert convert_page.task_combo.itemText(1) == "obb"
    assert convert_page.task_combo.currentText() == "detect"
    assert train_page.pretrained_combo.currentText() == "yolov8s.pt"
    assert train_page.edits["epochs"].text() == "500"
    assert train_page.edits["patience"].text() == "100"
    assert all(label.text() != "基础模型 ⓘ" for label in train_labels)
    assert all(label.text() != "图片目录 ⓘ" for label in convert_labels)


def test_readonly_logs_can_copy_selected_text_without_focus(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.training.page import TrainPage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
        refresh_help_icon_visibility=lambda: None,
    )

    train_page = TrainPage(fake_app)
    train_page.show()
    train_page.log.setPlainText("first line\nsecond line")
    cursor = train_page.log.textCursor()
    cursor.setPosition(0)
    cursor.setPosition(10, cursor.MoveMode.KeepAnchor)
    train_page.log.setTextCursor(cursor)

    clipboard = app.clipboard()
    clipboard.clear()
    train_page.log._copy_shortcut.activated.emit()

    assert int(train_page.log.focusPolicy()) == int(train_page.log.focusPolicy().NoFocus)
    assert clipboard.text() == "first line"


def test_help_icon_toggle_updates_visibility(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication, QLabel
    from src.ui.features.settings.page import SettingsPage
    from src.ui.features.training.page import TrainPage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    saved = {}

    class FakeApp(SimpleNamespace):
        def refresh_help_icon_visibility(self):
            for page in self.pages:
                page.refresh_help_icon_visibility()

    fake_app = FakeApp(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda data: saved.update(data)),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
        pages=[],
    )

    train_page = TrainPage(fake_app)
    settings_page = SettingsPage(fake_app)
    fake_app.pages = [train_page, settings_page]
    before_labels = [label.text() for label in train_page.findChildren(QLabel)]
    assert "训练轮数 ⓘ" in before_labels

    settings_page.help_icon_check.setChecked(False)

    assert fake_app.settings["features"]["show_help_icons"] is False
    assert saved["features"]["show_help_icons"] is False
    after_labels = [label.text() for label in train_page.findChildren(QLabel)]
    assert "训练轮数 ⓘ" not in after_labels
    assert "训练轮数" in after_labels
    epoch_label = next(
        label for label in train_page.findChildren(QLabel) if label.text() == "训练轮数"
    )
    assert (
        epoch_label.toolTip()
        == "训练轮数（epochs）；设置完整训练的总轮次，更大通常效果更好，但训练耗时更长。"
    )


def test_workbench_window_uses_new_default_size():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.shared.qt import QApplication
    from src.ui.shell.window import WorkbenchWindow

    app = QApplication.instance() or QApplication([])
    window = WorkbenchWindow()

    assert window.width() == 1100
    assert window.height() == 740


def test_workbench_window_collects_program_logs():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.shared.qt import QApplication
    from src.ui.shell.window import WorkbenchWindow

    app = QApplication.instance() or QApplication([])
    window = WorkbenchWindow()
    window.append_program_log("测试日志", level="ERROR")

    text = window.program_log_text()
    assert "程序启动。" in text
    assert "[ERROR] 测试日志" in text


def test_workbench_window_close_event_skips_prompt_when_safe(monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtGui import QCloseEvent
    from src.shared.qt import QApplication
    from src.ui.shell.window import WorkbenchWindow

    app = QApplication.instance() or QApplication([])
    window = WorkbenchWindow()
    save_calls = {"count": 0}
    stop_calls = []

    monkeypatch.setattr(window.settings_service, "save", lambda _data: save_calls.__setitem__("count", save_calls["count"] + 1))
    monkeypatch.setattr("src.ui.shell.window.stop_process", lambda handle: stop_calls.append(handle))

    event = QCloseEvent()
    window.closeEvent(event)

    assert event.isAccepted() is True
    assert save_calls["count"] == 1
    assert len(stop_calls) == 3


def test_workbench_window_close_event_prompts_for_unsaved_annotations(monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtGui import QCloseEvent
    from src.shared.qt import QApplication, QMessageBox
    from src.ui.shell.window import WorkbenchWindow

    app = QApplication.instance() or QApplication([])
    window = WorkbenchWindow()
    annotation_widget = window.ensure_page("annotation")
    annotation_page = getattr(annotation_widget, "inner_page", annotation_widget)
    annotation_page.dirty = True
    asked = {"text": ""}
    save_calls = {"count": 0}

    def fake_question(_parent, _title, text, *_args, **_kwargs):
        asked["text"] = text
        return QMessageBox.StandardButton.No

    monkeypatch.setattr(QMessageBox, "question", fake_question)
    monkeypatch.setattr(window.settings_service, "save", lambda _data: save_calls.__setitem__("count", save_calls["count"] + 1))
    monkeypatch.setattr("src.ui.shell.window.stop_process", lambda _handle: None)

    event = QCloseEvent()
    window.closeEvent(event)

    assert event.isAccepted() is False
    assert save_calls["count"] == 0
    assert "当前有未保存的标注" in asked["text"]


def test_workbench_window_close_event_prompts_for_running_training(monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtGui import QCloseEvent
    from src.shared.qt import QApplication, QMessageBox
    from src.ui.shell.window import WorkbenchWindow

    app = QApplication.instance() or QApplication([])
    window = WorkbenchWindow()
    train_widget = window.ensure_page("train")
    train_page = getattr(train_widget, "inner_page", train_widget)
    train_page.is_training = True
    asked = {"text": ""}
    save_calls = {"count": 0}

    def fake_question(_parent, _title, text, *_args, **_kwargs):
        asked["text"] = text
        return QMessageBox.StandardButton.Yes

    monkeypatch.setattr(QMessageBox, "question", fake_question)
    monkeypatch.setattr(window.settings_service, "save", lambda _data: save_calls.__setitem__("count", save_calls["count"] + 1))
    monkeypatch.setattr("src.ui.shell.window.stop_process", lambda _handle: None)

    event = QCloseEvent()
    window.closeEvent(event)

    assert event.isAccepted() is True
    assert save_calls["count"] == 1
    assert "模型训练尚未结束" in asked["text"]


