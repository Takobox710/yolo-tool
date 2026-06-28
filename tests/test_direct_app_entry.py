from pathlib import Path


def test_app_file_has_direct_script_import_bootstrap():
    source = Path("scr/yolo_workbench/app.py").read_text(encoding="utf-8")

    assert "if __package__ in {None, \"\"}" in source
    assert "sys.path.insert" in source


def test_app_matches_reference_ui_sections():
    source = Path("scr/yolo_workbench/app.py").read_text(encoding="utf-8")

    for expected in [
        "欢迎使用 YOLO 本地训练工作台",
        "训练曲线",
        "马赛克",
        "图片/视频文件夹",
        "默认项目模板",
        "stat_card",
        "metric_card",
        "option_field",
        "CTkComboBox",
        "validate_layout",
        "批量检测结果",
        "save_current_result",
        "clear_results",
        "uniform=\"detect_buttons\"",
        "uniform=\"train_buttons\"",
    ]:
        assert expected in source

    assert '"nav": ("Microsoft YaHei UI", 15, "bold")' in Path("scr/yolo_workbench/theme.py").read_text(encoding="utf-8")
    assert 'text="开始训练", height=34, fg_color=COLORS["green"], text_color=COLORS["text"]' in source
    assert "最近活动" not in source
    assert "option_shell" not in source
    assert 'self.panel(action, "训练控制")' not in source
    assert 'self.panel(action, "系统状态")' not in source
    assert '"自动任务类型"' not in source
    assert 'self.stat_card(left_body, "任务类型"' not in source
    assert 'self.stat_card(overview_body, "任务类型"' not in source
    assert 'ctk.CTkButton(log_controls' not in source
    assert "header_builder=build_progress_header" in source
    assert "progress_side" not in source
    assert 'header.pack(fill="x", padx=8, pady=(8, 0))' in source
    assert 'header = ctk.CTkFrame(frame, fg_color=COLORS["panel"]' in source
    assert "progress_label" in source


def test_app_starts_at_minimum_window_size():
    app_source = Path("scr/yolo_workbench/app.py").read_text(encoding="utf-8")
    settings_source = Path("scr/yolo_workbench/services/settings_service.py").read_text(encoding="utf-8")

    assert "min(int(self.settings[\"ui\"].get(\"window_width\", 1100)), 1100)" in app_source
    assert "min(int(self.settings[\"ui\"].get(\"window_height\", 780)), 780)" in app_source
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
    assert 'app = "python -m scr.yolo_workbench_qt.main"' in pixi
    assert 'app-qt = "python -m scr.yolo_workbench_qt.main"' in pixi
    assert 'app-tk = "python -m scr.yolo_workbench.main"' in pixi
    assert 'pyside6 = ' in pixi


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
        "start_detection",
        "show_detection_payload",
        "save_current_result",
        "clear_results",
    ]:
        assert expected in qt_app
