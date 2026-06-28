from pathlib import Path


def test_app_file_has_direct_script_import_bootstrap():
    source = Path("scr/yolo_workbench/main.py").read_text(encoding="utf-8")

    assert "scr.yolo_workbench_qt.app" in source
    assert "run_app" in source


def test_qt_app_matches_reference_ui_sections():
    source = Path("scr/yolo_workbench_qt/app.py").read_text(encoding="utf-8")

    for expected in [
        "欢迎使用 YOLO 本地训练工作台",
        "配置项目路径、检查数据状态、查看训练结果。",
        "项目概览",
        "各类别图片分布",
        "训练曲线",
        "训练历史",
        "项目文件夹",
        "图片路径",
        "标注路径",
        "结果路径",
        "图片数量",
        "标签文件",
        "马赛克",
        "图片/视频文件夹",
        "QTabWidget",
        "QComboBox",
        "批量检测结果",
        "save_current_result",
        "clear_results",
        "模型配置 / 检测控制",
        "status_cards",
        "QStackedWidget",
        "数据集与增强配置",
        "训练参数",
        "训练日志",
        "headerProgress",
        "GPU",
        "显存占用",
        "CPU占用",
        "内存占用",
    ]:
        assert expected in source

    assert 'start = QPushButton("开始训练")' in source
    assert "最近活动" not in source
    assert '"自动任务类型"' not in source
    assert '"导出格式"' not in source
    assert 'Card("训练控制")' not in source
    assert 'Card("系统状态")' not in source
    assert 'Card("任务类型")' not in source
    assert "QProgressBar" in source


def test_app_starts_at_minimum_window_size():
    app_source = Path("scr/yolo_workbench_qt/app.py").read_text(encoding="utf-8")
    settings_source = Path("scr/yolo_workbench/services/settings_service.py").read_text(encoding="utf-8")

    assert "self.resize(1100, 780)" in app_source
    assert "self.setMinimumSize(1100, 780)" in app_source
    assert "\"window_width\": 1100" in settings_source
    assert "\"window_height\": 780" in settings_source


def test_qt_app_entry_and_task_are_available():
    qt_main = Path("scr/yolo_workbench_qt/main.py").read_text(encoding="utf-8")
    qt_app = Path("scr/yolo_workbench_qt/app.py").read_text(encoding="utf-8")
    pixi = Path("pixi.toml").read_text(encoding="utf-8")

    assert "from .app import run_app" in qt_main
    assert "QStackedWidget" in qt_app
    assert "SettingsService" in qt_app
    assert "build_train_command" in qt_app
    assert 'app = "python -m scr.yolo_workbench.main"' in pixi
    assert 'app-qt = "python -m scr.yolo_workbench_qt.main"' in pixi
    assert 'pyside6 = ' in pixi
    assert "app-tk" not in pixi
    assert "customtkinter" not in pixi
    assert not Path("scr/yolo_workbench/app.py").exists()


def test_qt_app_migrates_core_workbench_features():
    qt_app = Path("scr/yolo_workbench_qt/app.py").read_text(encoding="utf-8")

    for placeholder in [
        "业务按钮将继续复用现有服务层迁移",
        "后续迁移图像预览和结果表",
    ]:
        assert placeholder not in qt_app

    for expected in [
        "preview_conversion",
        "run_conversion",
        "render_annotation_preview",
        "preview_rename",
        "execute_rename",
        "preview_resize",
        "run_resize",
        "spawn_logged_process",
        "stop_process",
        "run_prediction",
        "QTabWidget",
        "QTableWidget",
        "QProgressBar",
        "QScrollArea",
        "QPixmap",
        "QImage",
        "QFileDialog",
        "QMessageBox",
        "DetectionWorker",
        "result_payload",
        "status_cards",
        "set_status_card",
        "start_detection",
        "show_detection_payload",
        "save_current_result",
        "clear_results",
    ]:
        assert expected in qt_app

    assert "self.log.setPlainText(json.dumps(payload" not in qt_app
    assert 'self.combo_field("基础模型"' in qt_app
    assert 'self.combo_field("设备"' in qt_app
    assert '"输出方式"' in qt_app
    assert '"保存格式"' in qt_app
