from pathlib import Path
import os
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
    assert "from .app import run_app" in src
    assert "run_app()" in src


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

    assert page.overview_stats["project"].toolTip() == str(tmp_path)
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
