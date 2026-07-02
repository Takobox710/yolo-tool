from pathlib import Path
import os
import subprocess
import sys
from types import SimpleNamespace

APP = Path("scr/ui/app.py")
ICON_PNG = Path("scr/assets/app_icon.png")
ICON_ICO = Path("scr/assets/app_icon.ico")
WINDOW = Path("scr/ui/window.py")
PAGE_BASE = Path("scr/ui/page_base.py")
HOME_VIEW = Path("scr/ui/views/home.py")
DATA_VIEW = Path("scr/ui/views/data.py")
TRAIN_VIEW = Path("scr/ui/views/training.py")
VALIDATE_VIEW = Path("scr/ui/views/validation.py")
SETTINGS_VIEW = Path("scr/ui/views/settings.py")
PACKAGING_SPEC = Path("packaging/YOLOTool.spec")
PACKAGING_DEV_SPEC = Path("packaging/YOLOTool.dev.spec")
PACKAGING_COMMON = Path("packaging/pyinstaller_common.py")
PACKAGING_SCRIPT = Path("packaging/build_windows.ps1")
PACKAGING_DEV_SCRIPT = Path("packaging/build_windows_dev.ps1")
PACKAGING_DOC = Path("docs/packaging-windows.md")


def _read_app():
    return APP.read_text(encoding="utf-8")


def _read_ui_bundle():
    paths = [APP, WINDOW, PAGE_BASE, HOME_VIEW, DATA_VIEW, TRAIN_VIEW, VALIDATE_VIEW, SETTINGS_VIEW]
    return "\n".join(path.read_text(encoding="utf-8") for path in paths)


def test_project_path_helpers_display_relative_and_resolve_user_text(tmp_path):
    from scr.ui.helpers import display_project_path, resolve_project_path

    inside = tmp_path / "data" / "data.yaml"
    outside = tmp_path.parent / "outside" / "model.pt"

    assert display_project_path(str(inside), tmp_path) == str(
        Path("data") / "data.yaml"
    )
    assert display_project_path(str(outside), tmp_path) == str(outside.resolve())
    assert Path(resolve_project_path("data/data.yaml", tmp_path)) == inside.resolve()
    assert (
        Path(resolve_project_path(str(inside).replace(os.sep, "/"), tmp_path))
        == inside.resolve()
    )


def test_qt_app_uses_project_local_icon_assets():
    src = _read_ui_bundle()
    assert (
        'icon_path = Path(__file__).resolve().parent.parent / "assets" / "app_icon.png"'
        in src
    )
    assert "self.setWindowIcon(app_icon)" in src
    assert ICON_PNG.exists()
    assert ICON_ICO.exists()


def test_app_file_has_direct_script_import_bootstrap():
    src = Path("scr/main.py").read_text(encoding="utf-8")
    assert "freeze_support()" in src
    assert "from scr.app import run_app" in src
    assert "run_app()" in src


def test_direct_script_hidden_train_entry_has_package_context():
    result = subprocess.run(
        [sys.executable, "scr/main.py", "--yolo-train"],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode != 0
    assert "Usage: --yolo-train" in result.stderr
    assert "attempted relative import" not in result.stderr


def test_windows_packaging_files_document_project_local_runtime_settings():
    assert PACKAGING_SPEC.exists()
    assert PACKAGING_DEV_SPEC.exists()
    assert PACKAGING_COMMON.exists()
    assert PACKAGING_SCRIPT.exists()
    assert PACKAGING_DEV_SCRIPT.exists()
    assert PACKAGING_DOC.exists()

    spec = PACKAGING_SPEC.read_text(encoding="utf-8")
    dev_spec = PACKAGING_DEV_SPEC.read_text(encoding="utf-8")
    common = PACKAGING_COMMON.read_text(encoding="utf-8")
    script = PACKAGING_SCRIPT.read_text(encoding="utf-8")
    dev_script = PACKAGING_DEV_SCRIPT.read_text(encoding="utf-8")
    doc = PACKAGING_DOC.read_text(encoding="utf-8")

    assert "onedir" in doc
    assert "Mode dev" in doc or "-Mode dev" in doc
    assert "YOLOTool-dev" in doc
    assert "data/runtime/settings.json" in doc
    assert "scr/main.py" in spec
    assert 'build_packaging("release")' in spec
    assert 'build_packaging("dev")' in dev_spec
    assert "PySide6.scripts.deploy_lib" in common
    assert "torch.utils.tensorboard" in common
    assert "excludedimports = [\"torch.utils.tensorboard\"]" in Path("packaging/hooks/hook-torch.py").read_text(encoding="utf-8")
    assert "pyinstaller" in script
    assert 'ValidateSet("release", "dev")' in script
    assert "build_windows.ps1" in dev_script


def test_qt_app_matches_reference_ui_sections():
    src = _read_ui_bundle()
    for expected in [
        "欢迎使用 YOLO 本地训练工作台",
        "项目概览",
        "各类别图片分布",
        "训练历史",
        "项目文件夹",
        "图片路径",
        "标注路径",
        "结果路径",
        "图片数量",
        "标签文件",
        "马赛克",
        "图片/视频文件夹",
        "QComboBox",
        "tool_stack",
        "dataNavButton",
        "show_tool",
        "标注转换",
        "标注预览",
        "批量重命名",
        "图片压缩",
        "批量检测结果",
        "show_result_list",
        "open_detection_save_dir",
        "模型配置",
        "检测日志",
        "源",
        "检测结果",
        "检测结果详情表",
        "status_cards",
        "QStackedWidget",
        "数据集与增强配置",
        "训练参数",
        "GPU",
        "显存占用",
        "CPU占用",
        "内存占用",
        "inline_field",
        "inline_combo_field",
        "short_gpu_name",
        "left_shell = Card()",
    ]:
        assert expected in src
    assert 'self.start_btn = QPushButton("开始训练")' in src
    assert "sidebar.setFixedWidth(180)" in src
    assert 'title = QLabel("模型训练")' not in src
    assert 'title = QLabel("模型验证")' not in src
    assert "最近活动" not in src
    assert '"自动任务类型"' not in src
    assert '"导出格式"' not in src
    assert 'Card("训练控制")' not in src
    assert 'Card("系统状态")' not in src
    assert 'Card("任务类型")' not in src
    assert "log_panel = Card()" in src
    assert 'Card("训练日志")' not in src
    assert 'Card("训练曲线")' not in src
    assert "TrainingCurveWidget" in src
    assert "配置项目路径、检查数据状态、查看训练结果。" not in src


def test_ui_modules_are_split_by_window_and_navigation_pages():
    app_src = _read_app()
    assert WINDOW.exists()
    assert PAGE_BASE.exists()
    assert HOME_VIEW.exists()
    assert DATA_VIEW.exists()
    assert TRAIN_VIEW.exists()
    assert VALIDATE_VIEW.exists()
    assert SETTINGS_VIEW.exists()
    assert "from scr.ui.window import WorkbenchWindow, build_style" in app_src
    assert "from scr.ui.views.home import HomePage" not in app_src
    assert "class WorkbenchWindow" not in app_src
    assert "class HomePage" not in app_src
    assert "class DataPage" not in app_src
    assert "class TrainPage" not in app_src
    assert "class ValidatePage" not in app_src
    assert "class SettingsPage" not in app_src
    assert APP.stat().st_size < 12000


def test_page_base_reexports_shared_widgets():
    from scr.ui.page_base import Card, ImageView
    from scr.ui.widgets.base import Card as WidgetCard
    from scr.ui.widgets.base import ImageView as WidgetImageView

    assert Card is WidgetCard
    assert ImageView is WidgetImageView


def test_home_page_can_be_constructed_and_refreshed(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication, QSizePolicy
    from scr.ui.views.home import HomePage

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
    assert page.minimumHeight() == 650
    assert margins.left() == 16
    assert margins.top() == 16
    assert margins.right() == 16
    assert margins.bottom() == 4
    assert all(
        card.sizePolicy().verticalPolicy() == QSizePolicy.Policy.Preferred
        for card in page._home_left_cards + page._home_right_cards
    )


def test_main_pages_can_be_constructed(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication
    from scr.ui.views.data import DataPage
    from scr.ui.views.settings import SettingsPage
    from scr.ui.views.training import TrainPage
    from scr.ui.views.validation import ValidatePage

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
    assert validate_page.start_det_btn.text() == "批量检测"
    assert "Pixi" in settings_page.status_cards
    assert settings_page.help_icon_check.isChecked() is True


def test_workbench_window_preloads_all_pages():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.ui.qt import QApplication
    from scr.ui.window import WorkbenchWindow

    app = QApplication.instance() or QApplication([])
    window = WorkbenchWindow()

    assert list(window.pages.keys()) == window.page_order
    assert window.stack.count() == len(window.page_order)


def test_workbench_window_switches_to_project_local_settings(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    import json

    from scr.ui.qt import QApplication
    from scr.ui.window import WorkbenchWindow

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
    assert list(window.pages.keys()) == window.page_order


def test_workbench_window_restores_last_selected_project_root_on_restart(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    import json

    from scr.services import settings_service
    from scr.ui.qt import QApplication
    from scr.ui.window import WorkbenchWindow

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


def test_scheme_b_uses_label_tooltips_instead_of_help_icon():
    src = PAGE_BASE.read_text(encoding="utf-8")
    assert "class HelpIcon" not in src
    assert "ⓘ" in src


def test_pages_add_placeholders_and_help_icons(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication, QCheckBox, QLabel
    from scr.ui.views.convert import ConvertTab
    from scr.ui.views.preview import PreviewTab
    from scr.ui.views.rename import RenameTab
    from scr.ui.views.resize import ResizeTab
    from scr.ui.views.settings import SettingsPage
    from scr.ui.views.training import TrainPage
    from scr.ui.views.validation import ValidatePage

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
    assert rename_page.prefix_edit.placeholderText() == "例如 weld"
    assert resize_page.long_edit.placeholderText() == "例如 960"
    assert validate_page.conf_edit.placeholderText() == "例如 0.25"
    assert int(convert_page.log.focusPolicy()) == int(convert_page.log.focusPolicy().NoFocus)
    assert int(resize_page.log.focusPolicy()) == int(resize_page.log.focusPolicy().NoFocus)
    assert int(validate_page.detect_log.focusPolicy()) == int(validate_page.detect_log.focusPolicy().NoFocus)
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
    assert len(train_labels) == 8
    assert len(train_checks) == 8
    assert len(convert_labels) == 6
    assert len(preview_labels) == 0
    assert len(rename_labels) == 0
    assert len(resize_labels) == 0
    assert len(validate_labels) == 0
    assert len(settings_labels) == 0
    assert any(label.text() == "Epochs ⓘ" and label.toolTip() == "控制训练轮数（epochs）；更大通常效果更好，但训练耗时更长。" for label in train_labels)
    assert any(label.text() == "Workers ⓘ" and label.toolTip() == "数据加载线程数（workers）；提高后通常更快，但会占用更多 CPU 和系统内存。" for label in train_labels)
    assert any(label.text() == "图片尺寸 ⓘ" and label.toolTip() == "训练输入尺寸（imgsz）；更大可能更准，但更吃显存，也会占用更多系统内存和时间。" for label in train_labels)
    assert any(check.text() == "马赛克 ⓘ" and check.toolTip() == "随机拼图增强（mosaic）；将多张图随机拼接成一张，增强小目标和复杂场景鲁棒性。" for check in train_checks)
    assert convert_page.labelme_check.text() == "Labelme 转 YOLO ⓘ"
    assert convert_page.labelme_check.toolTip() == "开启时自动识别 Labelme 类别并转换为 YOLO；关闭时只对已有 YOLO txt 标注重新分组。"
    assert all(label.text() != "基础模型 ⓘ" for label in train_labels)
    assert all(label.text() != "图片目录 ⓘ" for label in convert_labels)


def test_convert_page_keeps_yolo_path_editable_when_labelme_mode_changes(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication
    from scr.ui.views.convert import ConvertTab

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        refresh_help_icon_visibility=lambda: None,
    )

    page = ConvertTab(fake_app)

    assert page.yolo_labels_box.isEnabled() is True
    assert page.yolo_labels_edit.isEnabled() is True
    assert page.line_edit.isEnabled() is True

    page.labelme_check.setChecked(False)

    assert page.yolo_labels_box.isEnabled() is True
    assert page.yolo_labels_edit.isEnabled() is True
    assert page.line_edit.isEnabled() is False


def test_help_icon_toggle_updates_visibility(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication, QLabel
    from scr.ui.views.settings import SettingsPage
    from scr.ui.views.training import TrainPage

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
    assert "Epochs ⓘ" in before_labels

    settings_page.help_icon_check.setChecked(False)

    assert fake_app.settings["features"]["show_help_icons"] is False
    assert saved["features"]["show_help_icons"] is False
    after_labels = [label.text() for label in train_page.findChildren(QLabel)]
    assert "Epochs ⓘ" not in after_labels
    assert "Epochs" in after_labels
    epoch_label = next(
        label for label in train_page.findChildren(QLabel) if label.text() == "Epochs"
    )
    assert (
        epoch_label.toolTip()
        == "控制训练轮数（epochs）；更大通常效果更好，但训练耗时更长。"
    )


def test_workbench_window_uses_new_default_size():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.ui.qt import QApplication
    from scr.ui.window import WorkbenchWindow

    app = QApplication.instance() or QApplication([])
    window = WorkbenchWindow()

    assert window.width() == 1100
    assert window.height() == 770


def test_train_page_resolves_model_file_from_data_models(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.services.settings_service import build_default_settings
    from scr.services.training_service import build_train_command
    from scr.ui.qt import QApplication
    from scr.ui.views.training import TrainPage

    model_path = tmp_path / "data" / "models" / "yolov8m-obb.pt"
    model_path.parent.mkdir(parents=True)
    model_path.write_text("weights", encoding="utf-8")

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    settings["training"]["model_yaml"] = ""
    settings["training"]["pretrained"] = model_path.name
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
    )

    page = TrainPage(fake_app)
    command = build_train_command(page.collect_config())

    assert f"model={model_path}" in command
    assert f"pretrained={model_path}" in command


def test_command_dialog_uses_wider_size():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.ui.dialogs import CommandDialog
    from scr.ui.qt import QApplication

    app = QApplication.instance() or QApplication([])
    dialog = CommandDialog(["pixi", "run", "yolo", "detect", "train"])

    assert dialog.minimumWidth() == 350
    assert dialog.minimumHeight() == 100
    assert dialog.width() == 700
    assert dialog.height() == 200


def test_training_page_persists_updated_fields_to_settings(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication
    from scr.ui.views.training import TrainPage

    app = QApplication.instance() or QApplication([])
    saved = {}
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda data: saved.update(data)),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
    )

    page = TrainPage(fake_app)
    page.edits["epochs"].setText("123")
    page.pretrained_combo.setCurrentText("custom.pt")

    assert fake_app.settings["training"]["epochs"] == "123"
    assert Path(fake_app.settings["training"]["pretrained"]).name == "custom.pt"
    assert "training" in saved


def test_validation_page_lists_models_from_data_models_first(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication
    from scr.ui.views.validation import ValidatePage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    models_dir = tmp_path / "data" / "models"
    models_dir.mkdir(parents=True)
    (models_dir / "alpha.pt").write_text("a", encoding="utf-8")
    (tmp_path / "result" / "train" / "weights").mkdir(parents=True)
    (tmp_path / "result" / "train" / "weights" / "best.pt").write_text(
        "b", encoding="utf-8"
    )
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
    )

    page = ValidatePage(fake_app)
    page.on_show()

    assert page.model_combo.itemText(0) == "data\\models\\alpha.pt"
