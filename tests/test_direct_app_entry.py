from pathlib import Path


def test_qt_app_uses_project_local_icon_assets_first():
    source = Path("scr/yolo_workbench_qt/app.py").read_text(encoding="utf-8")
    icon_png = Path("scr/yolo_workbench_qt/assets/app_icon.png")
    icon_ico = Path("scr/yolo_workbench_qt/assets/app_icon.ico")

    assert "PACKAGE_ROOT = Path(__file__).resolve().parent" in source
    assert "APP_ICON_PATHS = [" in source
    assert 'PACKAGE_ROOT / "assets" / "app_icon.ico"' in source
    assert 'PACKAGE_ROOT / "assets" / "app_icon.png"' in source
    assert source.index('PACKAGE_ROOT / "assets" / "app_icon.ico"') < source.index('LEGACY_TOOL_ROOT / "icon.ico"')
    assert icon_png.exists()
    assert icon_ico.exists()


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
        "QComboBox",
        "tool_stack",
        "dataNavButton",
        "show_tool",
        "标注转换",
        "标注预览",
        "批量重命名",
        "图片压缩",
        "批量检测结果",
        "save_current_result",
        "clear_results",
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
        assert expected in source

    assert 'start = QPushButton("开始训练")' in source
    assert "sidebar.setFixedWidth(180)" in source
    assert 'title = QLabel("模型训练")' not in source
    assert 'title = QLabel("模型验证")' not in source
    assert "最近活动" not in source
    assert '"自动任务类型"' not in source
    assert '"导出格式"' not in source
    assert 'Card("训练控制")' not in source
    assert 'Card("系统状态")' not in source
    assert 'Card("任务类型")' not in source
    assert 'Card("模型配置")' not in source
    assert 'Card("检测源配置")' not in source
    assert 'Card("检测控制")' not in source
    assert 'Card("检测日志")' not in source
    assert 'log_panel = Card()' in source
    assert 'Card("训练日志")' not in source


def test_qt_app_keeps_latest_ui_regressions_fixed():
    source = Path("scr/yolo_workbench_qt/app.py").read_text(encoding="utf-8")

    assert 'QLabel("检测源配置")' not in source
    assert 'QLabel("检测控制")' not in source
    assert 'box, edit = self.field(label, self.format_project_path(training.get(key, "")), browse)' in source
    assert 'card, value = self.stat_card(label, multiline=True)' in source
    assert 'history = Card()' in source
    assert 'history_header = QHBoxLayout()' in source
    assert 'history_header.addWidget(QLabel("训练历史"))' in source
    assert 'overview = Card()' in source
    assert 'overview_header = QHBoxLayout()' in source
    assert 'overview_header.addWidget(QLabel("项目概览"))' in source
    assert 'overview_header.addWidget(pick)' in source


def test_qt_train_page_keeps_spacing_and_status_cards_layout():
    source = Path("scr/yolo_workbench_qt/app.py").read_text(encoding="utf-8")

    assert 'label_width=72' in source
    assert 'params.setHorizontalSpacing(28)' in source
    assert 'params.setVerticalSpacing(12)' in source
    assert 'status = Card()' in source
    assert 'status_row = QHBoxLayout()' in source
    assert 'status_row.setSpacing(12)' in source
    assert 'card, metric = self.metric_card(label, outer=False)' in source
    assert 'status.layout.addLayout(status_row)' in source
    assert 'actions.addWidget(status, 3)' in source


def test_qt_metric_cards_keep_border_style():
    source = Path("scr/yolo_workbench_qt/app.py").read_text(encoding="utf-8")

    assert '#metricCard { background: #F5F8FB; border: 1px solid #D9E3EC; border-radius: 8px; }' in source
    assert 'status.setObjectName("statusShell")' in source
    assert '#statusShell { background: white; border: 1px solid #D9E3EC; border-radius: 8px; }' in source


def test_qt_home_and_training_polish_regressions():
    source = Path("scr/yolo_workbench_qt/app.py").read_text(encoding="utf-8")

    assert "def format_project_path(self, value: str):" in source
    assert 'return scroll_page(HomePage(self))' in source
    assert 'card.setMinimumHeight(24)' in source
    assert 'box, edit = self.field(label, self.format_project_path(training.get(key, "")), browse)' in source
    assert 'layout = QHBoxLayout(card)' in source
    assert 'name.setFixedWidth(74)' in source
    assert 'metric.setWordWrap(True)' in source
    assert '("project", self.app.settings["project"]["root"]),' in source
    assert '("images", self.format_project_path(paths["images_dir"])),' in source
    assert 'self.log = QTextEdit()' in source
    assert 'log_panel = Card()' in source
    assert 'Card("训练日志")' not in source
    assert "headerProgress" not in source
    assert 'self.status_refresh_inflight = False' in source
    assert 'if self.status_refresh_inflight:' in source
    assert 'self.status_refresh_inflight = True' in source
    assert 'self.status_refresh_inflight = False' in source
    assert 'self.setWindowIcon(' in source
    assert 'brand_icon = QLabel()' in source
    assert 'brand_row = QHBoxLayout()' in source
    assert 'dashboard.setRowStretch(0, 58)' in source
    assert 'dashboard.setRowStretch(1, 42)' in source
    assert 'dashboard.setColumnStretch(0, 1)' in source
    assert 'dashboard.setColumnStretch(1, 2)' in source
    assert 'def update_dashboard_stretch(self):' in source
    assert 'self.update_dashboard_stretch()' in source
    assert 'self.distribution_view = PaintView(self.render_distribution_chart)' in source
    assert 'self.curve_view = PaintView(self.render_training_curve)' in source
    assert 'w = max(rect.width(), 320)' in source
    assert 'h = max(rect.height(), 180)' in source
    assert 'self.distribution_view.update()' in source
    assert 'self.curve_view.update()' in source


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
    assert 'self.inline_combo_field("基础模型"' in qt_app
    assert 'self.inline_combo_field("设备"' in qt_app
    assert '"输出方式"' in qt_app
    assert '"保存格式"' in qt_app

def test_qt_train_page_refreshes_system_status_every_3_seconds():
    source = Path("scr/yolo_workbench_qt/app.py").read_text(encoding="utf-8")

    assert "self.status_refresh_timer = QTimer(self)" in source
    assert "self.status_refresh_timer.timeout.connect(self.request_train_status)" in source
    assert "def request_train_status(self):" in source
    assert "self.request_train_status()" in source
    assert "self.status_refresh_timer.start(500)" in source
    assert "def on_hide(self):" in source
    assert "self.status_refresh_timer.stop()" in source
    assert "self.status_refresh_inflight = False" in source
    assert "previous = self.stack.currentWidget()" in source
    assert 'hide_hook = getattr(previous_page, "on_hide", None)' in source
