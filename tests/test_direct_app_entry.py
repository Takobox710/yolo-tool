from pathlib import Path
import os


APP = Path("scr/yolo_workbench_qt/app.py")
HOME_CHARTS = Path("scr/yolo_workbench_qt/home_charts.py")
SETTINGS = Path("scr/yolo_workbench/services/settings_service.py")
ICON_PNG = Path("scr/yolo_workbench_qt/assets/app_icon.png")
ICON_ICO = Path("scr/yolo_workbench_qt/assets/app_icon.ico")


def _read_app():
    return APP.read_text(encoding="utf-8")


def _read_home_charts():
    return HOME_CHARTS.read_text(encoding="utf-8")


def test_project_path_helpers_display_relative_and_resolve_user_text(tmp_path):
    from scr.yolo_workbench_qt.app import _display_project_path, _resolve_project_path

    inside = tmp_path / "data" / "data.yaml"
    outside = tmp_path.parent / "outside" / "model.pt"

    assert _display_project_path(str(inside), tmp_path) == str(Path("data") / "data.yaml")
    assert _display_project_path(str(outside), tmp_path) == str(outside.resolve())
    assert Path(_resolve_project_path("data/data.yaml", tmp_path)) == inside.resolve()
    assert Path(_resolve_project_path(str(inside).replace(os.sep, "/"), tmp_path)) == inside.resolve()


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
        "项目概览", "各类别图片分布", "训练历史",
        "项目文件夹", "图片路径", "标注路径", "结果路径", "图片数量", "标签文件",
        "马赛克", "图片/视频文件夹", "QComboBox", "tool_stack", "dataNavButton", "show_tool",
        "标注转换", "标注预览", "批量重命名", "图片压缩",
        "批量检测结果", "show_result_list", "open_detection_save_dir",
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
    assert 'Card("训练曲线")' not in src
    assert "TrainingCurveWidget" in src
    assert "配置项目路径、检查数据状态、查看训练结果。" not in src


def test_page_on_show_runs_after_initial_layout_settles():
    src = _read_app()
    assert "QTimer.singleShot(0, hook)" in src
    assert "hook()" not in src


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


def test_training_path_fields_and_augment_order_are_locked():
    src = _read_app()
    assert 'base_box, self.pretrained_combo = self.stacked_combo_field(\n                "基础模型", current_name, model_files,\n                browse=lambda combo: self._choose_pt_for_combo(combo),\n                placeholder="选择或输入 .pt 模型")' in src
    assert 'self.stacked_path_field("数据集YAML", training.get("data", ""), self.choose_file, "选择 data.yaml")' in src
    assert 'self.stacked_path_field("模型YAML", "", self.choose_file, "可选，留空使用基础模型")' in src
    assert 'self.stacked_path_field("项目输出", training.get("project", ""), self.choose_dir, "选择训练结果输出目录")' in src
    assert '[("mosaic", "马赛克"), ("scale", "缩放"), ("translate", "平移"), ("hsv_h", "HSV"), ("fliplr", "左右翻转"), ("flipud", "上下翻转"), ("degrees", "旋转"), ("mixup", "MixUp")]' in src


def test_training_history_default_sort_uses_newer_ids_and_best_first():
    from scr.yolo_workbench_qt.app import _history_model_sort_key

    ordered = sorted(
        [
            ("train", "best.pt"),
            ("train-2", "last.pt"),
            ("train-2", "best.pt"),
            ("train", "last.pt"),
        ],
        key=lambda item: _history_model_sort_key(*item),
    )

    assert ordered == [
        ("train-2", "best.pt"),
        ("train-2", "last.pt"),
        ("train", "best.pt"),
        ("train", "last.pt"),
    ]


def test_hsv_checkbox_controls_all_hsv_train_command_params():
    src = _read_app()
    assert 'config["hsv_h"] = self.app.settings["training"].get("hsv_h", 0) if hsv_enabled else 0' in src
    assert 'config["hsv_s"] = self.app.settings["training"].get("hsv_s", 0) if hsv_enabled else 0' in src
    assert 'config["hsv_v"] = self.app.settings["training"].get("hsv_v", 0) if hsv_enabled else 0' in src


def test_validation_layout_keeps_left_column_compact_and_results_two_to_one():
    src = _read_app()
    assert 'self.model_combo.setMinimumWidth(140)' in src
    assert 'split.setStretch(0, 2)' in src
    assert 'split.setStretch(1, 7)' in src
    assert 'right.addLayout(views, 2)' in src
    assert 'right.addWidget(table_panel, 1)' in src


def test_validation_model_picker_uses_stacked_combo_and_no_source_title():
    src = _read_app()
    assert 'model_box, self.model_combo = self.stacked_combo_field(\n                "选择模型", "", [],\n                browse=lambda combo: self._choose_pt_for_combo(combo),\n                placeholder="选择或输入模型路径")' in src
    assert 'left_column.addWidget(model_box)' in src
    assert 'model_row = QHBoxLayout()' not in src
    assert 'QLabel("检测源配置")' not in src
    assert '"检测源配置"' not in src


def test_validation_detection_toolbar_modes_and_table_columns():
    src = _read_app()
    assert '["图片/视频文件夹", "图片/视频", "摄像头"]' in src
    assert '"source_mode": self.mode_combo.currentText()' in src
    assert 'self.choose_detection_source' in src
    assert 'self.start_det_btn = QPushButton("批量检测")' in src
    assert 'self.update_detection_button_text()' in src
    assert '[("上一张", self.prev_result), ("下一张", self.next_result), ("第一张", self.first_result), ("最后一张", self.last_result), ("列表", self.show_result_list), ("打开保存文件夹", self.open_detection_save_dir)]' in src
    assert 'self.table = QTableWidget(0, 5)' in src
    assert 'self.table.setHorizontalHeaderLabels(["类别", "置信度", "坐标(x,y)", "尺寸(w×h)", "角度"])' in src
    assert 'row + 1, item.label' not in src
    assert 'clear_results' not in src
    assert 'QPushButton("清空结果")' not in src


def test_validation_source_list_drives_single_file_detection():
    src = _read_app()
    assert 'self.source_items: list[Path] = []' in src
    assert 'self.result_by_source: dict[str, dict] = {}' in src
    assert 'def refresh_source_items(self):' in src
    assert 'self.source_items = collect_prediction_sources(self.mode_combo.currentText(), self.resolve_path_text(self.source_edit))' in src
    assert 'dialog.resize(320, 520)' in src
    assert 'dialog.setMinimumSize(200, 200)' in src
    assert 'search = QLineEdit()' in src
    assert 'search.setPlaceholderText("搜索文件名")' in src
    assert 'listing.addItem(path.name)' in src
    assert 'listing.addItem(f"{index}. {name}")' not in src
    assert 'search.textChanged.connect(filter_items)' in src
    assert 'def show_source_index(self, index: int):' in src
    assert 'self.show_source_index(self.source_index + 1)' not in src
    assert 'self.show_source_index(self.source_index - 1)' not in src
    assert 'def update_detection_button_text(self):' in src
    assert 'self.start_det_btn.setText("开始检测" if self.mode_combo.currentText() == "图片/视频" else "批量检测")' in src
    assert 'def start_current_source_detection(self):' in src
    assert 'self.show_detection_payload(self.detect_results[self.detect_index])' in src
    assert 'self.start_single_detection(path)' not in src
    assert 'self.show_cached_source_result(path)' in src
    assert 'def show_cached_source_result(self, path: Path) -> bool:' in src
    assert 'self.detect_index = self.detect_results.index(cached)' in src


def test_detection_batch_navigation_keeps_user_selected_result_visible():
    src = _read_app()
    assert 'self.is_batch_detection = False' in src
    assert 'self.is_batch_detection = True' in src
    assert 'self.user_selected_result = False' in src
    assert 'self.user_selected_result = True' in src
    assert 'if len(self.detect_results) == 1 or (not self.is_batch_detection and not self.user_selected_result):' in src
    assert 'if len(self.detect_results) == 1 or (not self.is_batch_detection and not self.user_selected_result):\n                self.detect_index = len(self.detect_results) - 1\n                self.show_detection_payload(payload)' in src
    assert 'else:\n                # Just update counter and log, don\'t switch view' in src


def test_path_inputs_resolve_relative_text_before_running_services():
    src = _read_app()
    assert 'return Path(self.resolve_path_text(edit))' in src
    assert 'config["data"] = self.resolve_path_text(self.edits["data"]) if self.edits["data"] else ""' in src
    assert 'config["project"] = self.resolve_path_text(self.edits["project"]) if self.edits["project"] else ""' in src
    assert '"source_path": self.resolve_path_text(self.source_edit),' in src


def test_qt_metric_cards_keep_border_style():
    src = _read_app()
    assert '#metricCard { background: #F5F8FB; border: 1px solid #E8EDF2; border-radius: 6px; }' in src
    assert '#systemInfoOuter { background: white; border: 1px solid #D9E3EC; border-radius: 8px; }' in src
    assert '#systemInfoInner { background: #F0F2F5; border: 1px solid #E0E3E8; border-radius: 6px; }' in src
    assert 'QLineEdit, QTextEdit, QComboBox, QTableWidget { background: white; border: 1px solid #CFD9E3; border-radius: 5px; padding: 7px; }' in src
    assert 'QTableWidget { background: #FFFFFF; alternate-background-color: #F7FAFC; gridline-color: #E1E8F0; selection-background-color: #DCEEFF; selection-color: #0D2B49; }' in src
    assert 'QTableWidget::item { padding: 6px; border-bottom: 1px solid #E8EDF2; }' in src
    assert 'QTableWidget::item:hover { background: #EEF6FF; }' in src
    assert 'QHeaderView::section { background: #EAF1F8; color: #0D2B49; border: 0; border-right: 1px solid #D8E2EC; border-bottom: 1px solid #CBD8E4; padding: 7px 6px; font-weight: 700; }' in src


def test_qt_home_and_training_polish_regressions():
    src = _read_app()
    charts = _read_home_charts()
    assert 'return scroll_page(HomePage(self))' in src
    assert 'log_panel = Card()' in src
    assert 'Card("训练日志")' not in src
    assert 'headerProgress' not in src
    assert 'self.setWindowIcon(' in src
    assert 'nav_pix = _load_nav_icon()' in src
    assert 'grid.setRowStretch(0, 58)' in src
    assert 'grid.setRowStretch(1, 42)' in src
    assert 'grid.setColumnStretch(0, 1)' in src
    assert 'grid.setColumnStretch(1, 2)' in src
    assert 'TrainingCurveWidget' in src
    assert 'read_results_csv_for_curves' in src
    assert 'DatasetDistributionWidget' in src
    assert '"训练"' in charts
    assert '"验证"' in charts
    assert '"测试"' in charts
    assert 'self.is_training = False' in src
    assert 'self.start_btn.setEnabled(False)' in src
    assert 'CommandDialog' in src
    assert 'custom_command_dialog' in src
    assert '"第一张"' in src
    assert '"最后一张"' in src
    assert 'def first_result' in src
    assert 'def last_result' in src


def test_home_chart_rendering_is_extracted_from_home_page():
    src = _read_app()
    charts = _read_home_charts()
    assert 'from scr.yolo_workbench_qt.home_charts import DatasetDistributionWidget, TrainingCurveWidget' in src
    assert 'self.distribution_view = DatasetDistributionWidget()' in src
    assert 'self.curve_view = TrainingCurveWidget()' in src
    assert 'def draw_distribution' not in src
    assert 'def draw_training_curves' not in src
    assert 'class DatasetDistributionWidget(QLabel)' in charts
    assert 'class TrainingCurveWidget(QLabel)' in charts
    assert 'def set_counts(' in charts
    assert 'def set_curve_data(' in charts
    assert 'def resizeEvent(' in charts
    assert '暂无训练记录' in charts


def test_home_charts_use_bar_plot_and_compact_curve_card():
    src = _read_app()
    charts = _read_home_charts()
    assert 'Card("训练曲线")' not in src
    assert 'curve = Card()' in src
    assert 'self.distribution_view.setMinimumWidth' not in src
    assert 'self.curve_view.setMinimumWidth' not in src
    assert 'setMinimumWidth' not in charts
    assert 'max(self.width(), 520)' not in charts
    assert 'max(self.width(), 460)' not in charts
    assert 'drawRect' in charts
    assert "left = 30" in charts
    assert '"total": "总照片"' in charts
    assert '"total": QColor("#64748B")' in charts
    assert 'for index, split in enumerate(("total", "train", "val", "test"))' in charts
    assert 'chip_w' not in charts
    assert 'bar_x = 20' not in charts
    assert 'Epoch' in charts
    assert 'mAP50' in charts
    assert 'Box Loss' in charts


def test_training_curve_does_not_fill_lines_or_show_metric_values():
    charts = _read_home_charts()
    assert 'summary = [("Epoch", str(epoch_count or "-"))]' in charts
    assert '("mAP50", self._format_percent(self._last_value(map50)))' not in charts
    assert '("Box Loss", self._format_axis(self._last_value(box_loss)))' not in charts
    assert 'painter.setBrush(Qt.BrushStyle.NoBrush)' in charts
    assert 'painter.drawPath(path)' in charts


def test_training_curve_excludes_map5095_line():
    charts = _read_home_charts()
    assert 'map5095 = self._find_column("metrics/mAP50-95(")' not in charts
    assert 'mAP50-95' not in charts


def test_home_page_uses_compact_left_column():
    src = _read_app()
    assert "def _home_column_widths(" in src
    assert "left = content_width * 3 // 10" in src
    assert "right = content_width - left" in src
    assert "self._home_left_cards" in src
    assert "self._home_right_cards" in src
    assert "def resizeEvent(self, event)" in src
    assert "self._apply_home_column_widths()" in src
    assert ".setFixedWidth(left_width)" not in src
    assert ".setFixedWidth(right_width)" not in src
    assert "card.setMinimumWidth(0)" in src
    assert "card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)" in src
    assert "card.setMaximumWidth(left_width)" in src
    assert "card.setMaximumWidth(right_width)" in src


def test_home_page_scrolls_in_minimum_window_height():
    src = _read_app()
    assert 'return scroll_page(HomePage(self))' in src
    assert 'self.setMinimumHeight(700)' in src
    assert 'self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)' in src


def test_home_overview_text_fits_in_narrow_column():
    src = _read_app()
    assert "layout = QHBoxLayout(card)" in src
    assert "name.setFixedWidth(90)" in src
    assert "metric.setWordWrap(False)" in src
    assert "metric.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)" in src
    assert "pick.setFixedWidth(108)" in src
    assert "pick.setFixedHeight(30)" in src
    assert 'pick.setObjectName("compactSoftButton")' in src
    assert 'open_button.setObjectName("compactSoftButton")' in src
    assert 'open_button.setFixedWidth(120)' in src
    assert 'open_button.setFixedHeight(32)' in src
    assert 'QPushButton#compactSoftButton { background: #F5F8FB; color: #14233A; border: 1px solid #D9E3EC; border-radius: 5px; padding: 4px 10px; font-size: 14px; }' in src
    assert "self.overview_stats[key].setToolTip(text)" in src
    assert "def set_overview_stat(" in src
    assert "def _elide_overview_text(" in src
    assert "Qt.TextElideMode.ElideMiddle" in src


def test_app_starts_at_minimum_window_size():
    src = _read_app()
    settings_src = SETTINGS.read_text(encoding="utf-8")
    assert "self.resize(1100, 780)" in src
    assert "self.setMinimumSize(980, 720)" in src
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
        "show_detection_payload", "show_result_list", "open_detection_save_dir",
    ]:
        assert expected in src
    assert "self.log.setPlainText(json.dumps(payload" not in src
    assert 'self.pretrained_combo' in src  # created via stacked_combo_field
    assert 'self.optimizer_combo = QComboBox()' in src
    assert '"输出方式"' in src
    assert '"保存格式"' in src


def test_qt_train_page_refreshes_system_status():
    src = _read_app()
    assert 'self.train_status_timer = QTimer(self)' in src
    assert 'self.train_status_timer.timeout.connect(self.refresh_train_status)' in src
    assert 'self.train_status_timer.start(500)' in src
    assert 'def refresh_train_status(self):' in src
    assert 'self.app.run_background("train_status", lambda: {"status": system_status(), "cuda": torch_cuda_summary()})' in src
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
    assert "stacked_field" in src  # label-on-top pattern for 模型YAML
    # Task 13: system info styling
    assert '#systemInfoOuter' in src
    assert '#systemInfoInner' in src
    assert '_auto_refresh' in src
    # Task 14: batch processing optimization
    assert 'if len(self.detect_results) == 1 or (not self.is_batch_detection and not self.user_selected_result):' in src
    assert '"第一张"' in src
    assert '"最后一张"' in src


def test_training_history_refresh_and_sorting_regressions():
    src = _read_app()
    assert 'def _history_time_sort_key(' in src
    assert 'was_sorting = self.history_table.isSortingEnabled()' in src
    assert 'self.history_table.setSortingEnabled(False)' in src
    assert 'self.history_table.setSortingEnabled(was_sorting)' in src
    assert 'elif column == 2:' in src
    assert 'sort_key = _history_time_sort_key(value)' in src
    assert 'self.history_table.sortItems(0, Qt.SortOrder.AscendingOrder)' in src
    assert 'QPushButton#compactSoftButton { background: #F5F8FB; color: #14233A; border: 1px solid #D9E3EC; border-radius: 5px; padding: 4px 10px; font-size: 14px;' in src


def test_training_history_hides_sort_arrows_and_offsets_table():
    src = _read_app()
    assert 'history.layout.addSpacing(3)' in src
    assert 'QHeaderView::up-arrow { image: none; width: 0px; height: 0px; }' in src
    assert 'QHeaderView::down-arrow { image: none; width: 0px; height: 0px; }' in src


def test_horizontal_scroll_is_locked_and_history_time_fits():
    src = _read_app()
    assert "class PageScrollArea(QScrollArea):" in src
    assert "self.inner_page.setMaximumWidth(self.viewport().width())" in src
    assert 'scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)' in src
    assert 'self.history_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)' in src
    assert 'self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)' in src
    assert 'def _apply_history_column_widths(self):' in src
    assert 'weights = [170, 82, 128, 88, 112, 98, 88]' in src
    assert 'self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)' in src
    assert 'header.resizeSection(column, max(1, width))' in src
    assert 'QTimer.singleShot(0, self._apply_history_column_widths)' in src
    assert 'QTimer.singleShot(50, self._apply_history_column_widths)' in src
    assert 'available = max(1, self.history_table.viewport().width() - 2)' in src
    assert 'verticalScrollBar().sizeHint().width()' not in src
