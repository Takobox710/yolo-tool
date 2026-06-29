from pathlib import Path


APP = Path("scr/yolo_workbench_qt/app.py")
SETTINGS = Path("scr/yolo_workbench/services/settings_service.py")
ICON_PNG = Path("scr/yolo_workbench_qt/assets/app_icon.png")
ICON_ICO = Path("scr/yolo_workbench_qt/assets/app_icon.ico")


def _read_app():
    return APP.read_text(encoding="utf-8")


def test_qt_app_uses_project_local_icon_assets():
    src = _read_app()
    assert 'icon_path = Path(__file__).resolve().parent / "assets" / "app_icon.png"' in src
    assert 'self.setWindowIcon(app_icon)' in src
    assert ICON_PNG.exists()
    assert ICON_ICO.exists()


def test_app_file_has_direct_script_import_bootstrap():
    src = Path("scr/yolo_workbench/main.py").read_text(encoding="utf-8")
    assert "scr.yolo_workbench_qt.app" in src
    assert "run_app" in src


def test_qt_app_matches_reference_ui_sections():
    src = _read_app()
    for expected in [
        "欢迎使用 YOLO 本地训练工作台",
        "配置项目路径、检查数据状态、查看训练结果。",
        "项目概览", "各类别图片分布", "训练曲线", "训练历史",
        "项目文件夹", "图片路径", "标注路径", "结果路径", "图片数量", "标签文件",
        "马赛克", "图片/视频文件夹", "QComboBox", "tool_stack", "dataNavButton", "show_tool",
        "标注转换", "标注预览", "批量重命名", "图片压缩",
        "批量检测结果", "save_current_result", "clear_results",
        "模型配置", "检测日志", "源", "检测结果", "检测结果详情表",
        "status_cards", "QStackedWidget", "数据集与增强配置", "训练参数",
        "GPU", "显存占用", "CPU占用", "内存占用",
        "inline_field", "inline_combo_field", "short_gpu_name", "left_shell = Card()",
    ]:
        assert expected in src
    assert 'self.start_btn = QPushButton("开始训练")' in src
    assert 'sidebar.setFixedWidth(180)' in src
    assert 'title = QLabel("模型训练")' not in src
    assert 'title = QLabel("模型验证")' not in src
    assert "最近活动" not in src
    assert '"自动任务类型"' not in src
    assert '"导出格式"' not in src
    assert 'Card("训练控制")' not in src
    assert 'Card("系统状态")' not in src
    assert 'Card("任务类型")' not in src
    assert 'log_panel = Card()' in src
    assert 'Card("训练日志")' not in src


def test_qt_app_keeps_latest_ui_regressions_fixed():
    src = _read_app()
    assert 'history = Card()' in src
    assert 'overview = Card()' in src
    assert 'pick.clicked.connect(self.pick_project_root)' in src
    assert 'open_button.clicked.connect(self.open_result_dir)' in src
    assert 'header_row = QHBoxLayout()' in src
    assert 'ov_title = QLabel("项目概览")' in src
    assert 'hist_header = QHBoxLayout()' in src
    assert 'hist_title = QLabel("训练历史")' in src


def test_qt_train_page_keeps_spacing_and_status_cards_layout():
    src = _read_app()
    assert 'status = Card()' in src
    assert 'actions.addWidget(status, 3)' in src
    assert 'self.optimizer_combo = QComboBox()' in src
    assert '"优化器"' in src
    assert 'Card("训练日志")' not in src
    assert 'headerProgress' not in src


def test_qt_metric_cards_keep_border_style():
    src = _read_app()
    assert '#metricCard { background: #F5F8FB; border: 1px solid #E8EDF2; border-radius: 6px; }' in src
    assert '#systemInfoOuter { background: white; border: 1px solid #D9E3EC; border-radius: 8px; }' in src
    assert '#systemInfoInner { background: #F0F2F5; border: 1px solid #E0E3E8; border-radius: 6px; }' in src


def test_qt_home_and_training_polish_regressions():
    src = _read_app()
    assert 'return HomePage(self)' in src
    assert 'log_panel = Card()' in src
    assert 'Card("训练日志")' not in src
    assert 'headerProgress' not in src
    assert 'self.setWindowIcon(' in src
    assert 'nav_pix = _load_nav_icon()' in src
    assert 'grid.setRowStretch(0, 58)' in src
    assert 'grid.setRowStretch(1, 42)' in src
    assert 'grid.setColumnStretch(0, 1)' in src
    assert 'grid.setColumnStretch(1, 2)' in src
    assert 'draw_training_curves' in src
    assert 'read_results_csv_for_curves' in src
    assert 'draw_distribution' in src
    assert '"训练"' in src
    assert '"验证"' in src
    assert '"测试"' in src
    assert 'self.is_training = False' in src
    assert 'self.start_btn.setEnabled(False)' in src
    assert 'CommandDialog' in src
    assert 'custom_command_dialog' in src
    assert '"第一张"' in src
    assert '"最后一张"' in src
    assert 'def first_result' in src
    assert 'def last_result' in src


def test_app_starts_at_minimum_window_size():
    src = _read_app()
    settings_src = SETTINGS.read_text(encoding="utf-8")
    assert "self.resize(1100, 780)" in src
    assert "self.setMinimumSize(1100, 780)" in src
    assert '"window_width": 1100' in settings_src
    assert '"window_height": 780' in settings_src


def test_qt_app_entry_and_task_are_available():
    qt_main = Path("scr/yolo_workbench_qt/main.py").read_text(encoding="utf-8")
    src = _read_app()
    pixi = Path("pixi.toml").read_text(encoding="utf-8")
    assert "from .app import run_app" in qt_main
    assert "QStackedWidget" in src
    assert "SettingsService" in src
    assert "build_train_command" in src
    assert 'app = "python -m scr.yolo_workbench.main"' in pixi
    assert 'app-qt = "python -m scr.yolo_workbench_qt.main"' in pixi
    assert 'pyside6 = ' in pixi
    assert "app-tk" not in pixi
    assert "customtkinter" not in pixi
    assert not Path("scr/yolo_workbench/app.py").exists()


def test_qt_app_migrates_core_workbench_features():
    src = _read_app()
    for placeholder in ["业务按钮将继续复用现有服务层迁移", "后续迁移图像预览和结果表"]:
        assert placeholder not in src
    for expected in [
        "preview_conversion", "run_conversion", "render_annotation_preview",
        "preview_rename", "execute_rename", "preview_resize", "run_resize",
        "spawn_logged_process", "stop_process", "run_prediction",
        "QTableWidget", "QScrollArea", "QPixmap", "QImage",
        "QFileDialog", "QMessageBox", "DetectionWorker", "result_payload",
        "status_cards", "set_status_card", "start_detection",
        "show_detection_payload", "save_current_result", "clear_results",
    ]:
        assert expected in src
    assert "self.log.setPlainText(json.dumps(payload" not in src
    assert 'self.pretrained_combo = QComboBox()' in src
    assert 'self.optimizer_combo = QComboBox()' in src
    assert '"输出方式"' in src
    assert '"保存格式"' in src


def test_qt_train_page_refreshes_system_status():
    src = _read_app()
    assert 'self._auto_refresh_timer = QTimer(self)' in src
    assert 'self._auto_refresh_timer.start(500)' in src
    assert 'def _auto_refresh' in src


def test_new_features_present():
    """Verify all new task features are present in the code."""
    src = _read_app()
    # Task 3: relative paths
    assert 'def _relative_path(' in src
    assert 'def _simplified_model_path(' in src
    assert '_simplified_model_path' in src
    # Task 4: sort indicator hidden
    assert 'setSortIndicatorShown(False)' in src
    # Task 9: prevent double-start for detection too
    assert 'self.is_detecting = False' in src
    assert 'self.start_det_btn.setEnabled(False)' in src
    # Task 10: settings toggle for custom command dialog
    assert 'custom_command_dialog' in src
    assert 'QCheckBox()' in src
    # Task 11: no progress bar in train page
    assert 'headerProgress' not in src
    # Task 12: model YAML field with blank default
    assert '"模型YAML"' in src
    assert 'inline_field("模型YAML", "",' in src
    # Task 13: system info styling
    assert '#systemInfoOuter' in src
    assert '#systemInfoInner' in src
    assert '_auto_refresh' in src
    # Task 14: batch processing optimization
    assert 'if len(self.detect_results) == 1:' in src
    assert '"第一张"' in src
    assert '"最后一张"' in src
