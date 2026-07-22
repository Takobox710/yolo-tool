from __future__ import annotations

from pathlib import Path

from src.services.data_ops import relative_path_from_project, resolve_project_path
from src.services.validation import VIDEO_SUFFIXES, is_live_source_mode
from src.ui.shared.page_base import Card, ImageView
from src.shared.qt import (
    Qt,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QStyle,
    QTableWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from src.ui.features.validation.sources import (
    IMAGE_SOURCE_OPTIONS,
    SOURCE_SCOPE_OPTIONS,
    VIDEO_SOURCE_OPTIONS,
)
from src.ui.features.validation.video_player import VideoPlaybackController, VideoPlayer


def build_validation_layout(page, app) -> None:
    layout = page.page_layout()
    # Keep the page edge inset while removing the nested right-layout gutter.
    layout.setContentsMargins(16, 16, 16, 16)
    page.validation_layout = layout
    split = QHBoxLayout()
    page.validation_split_layout = split
    layout.addLayout(split, 1)

    left_shell = Card()
    page.left_shell = left_shell
    left_column = left_shell.layout
    page.left_column_layout = left_column
    validation = app.settings["validation"]
    stored_mode = validation.get("source_mode", "图片检测")
    if is_live_source_mode(stored_mode):
        stored_mode = "摄像头检测"
        validation["source_mode"] = stored_mode
    stored_source_path = validation.get("source_path", "")
    if stored_mode in {
        "图片检测",
        "视频检测",
        "图片文件夹",
        "视频文件夹",
        "图片/视频文件夹",
        "图片/视频",
    }:
        resolved_source = Path(
            resolve_project_path(stored_source_path, page.project_root())
        ) if stored_source_path else None
        if stored_mode in {"视频检测", "视频文件夹"}:
            stored_mode = "视频检测"
        elif stored_mode == "图片/视频" and resolved_source is not None:
            stored_mode = (
                "视频检测"
                if resolved_source.suffix.lower() in VIDEO_SUFFIXES
                else "图片检测"
            )
            if resolved_source.is_file():
                stored_source_path = str(resolved_source.parent)
        else:
            stored_mode = "视频检测" if stored_mode in {"视频检测", "视频文件夹"} else "图片检测"
        validation["source_mode"] = stored_mode
        validation["source_path"] = stored_source_path

    model_title = QLabel("模型配置")
    model_title.setObjectName("sectionTitle")
    model_title.setSizePolicy(
        QSizePolicy.Policy.Preferred,
        QSizePolicy.Policy.Fixed,
    )
    left_column.addWidget(model_title)
    model_box, page.model_combo = page.stacked_combo_field(
        "选择模型",
        "",
        [],
        browse=lambda combo: page._choose_pt_for_combo(combo),
        placeholder="选择或输入模型路径",
    )
    page.model_combo.setMinimumWidth(140)
    left_column.addWidget(model_box)

    conf_row = QHBoxLayout()
    page.conf_box, page.conf_edit = page.field(
        "置信度",
        str(validation["confidence"]),
        placeholder="例如 0.25",
    )
    page.iou_box, page.iou_edit = page.field(
        "IoU",
        str(validation["iou"]),
        placeholder="例如 0.45",
    )
    page.imgsz_box, page.imgsz_combo = page.combo_field(
        "图片尺寸",
        str(validation.get("imgsz", 640)),
        ["640", "960", "1280"],
        editable=True,
        placeholder="例如 640",
    )
    page.imgsz_combo.setMinimumContentsLength(5)
    conf_row.addWidget(page.conf_box)
    conf_row.addWidget(page.iou_box)
    conf_row.addWidget(page.imgsz_box)
    left_column.addLayout(conf_row)

    page.mode_box, page.mode_combo = page.combo_field(
        "检测模式",
        stored_mode,
        ["图片检测", "视频检测", "摄像头检测", "数据集验证"],
    )
    left_column.addWidget(page.mode_box)
    initial_source_text = (
        relative_path_from_project(validation["source_path"], page.project_root())
        if validation["source_path"]
        else validation.get(
            "source_selection",
            validation.get("source_scope", "全部图片"),
        )
    )
    initial_source_options = (
        VIDEO_SOURCE_OPTIONS if stored_mode == "视频检测" else IMAGE_SOURCE_OPTIONS
    )
    page.source_box, page.source_combo = page.stacked_combo_field(
        "输入源",
        initial_source_text,
        initial_source_options,
        browse=lambda combo: page.choose_detection_source(combo),
        placeholder="选择输入文件夹",
    )
    left_column.addWidget(page.source_box)
    page.data_box, page.data_edit = page.path_field(
        "数据集 YAML",
        validation.get("data", ""),
        page.choose_dataset_yaml,
        "选择 data.yaml",
    )
    left_column.addWidget(page.data_box)
    page.source_scope_box, page.source_scope_combo = page.stacked_combo_field(
        "选择验证源",
        validation.get("source_scope", "全部图片"),
        SOURCE_SCOPE_OPTIONS,
        browse=lambda combo: page.choose_validation_source(combo),
        placeholder="选择或输入验证文件夹",
    )
    left_column.addWidget(page.source_scope_box)
    page.camera_box, page.camera_combo = page.combo_field(
        "摄像头",
        str(validation["camera_index"]),
        ["0", "1", "2", "3"],
    )
    left_column.addWidget(page.camera_box)
    page.save_box, page.save_edit = page.path_field(
        "输出文件夹",
        validation["save_dir"],
        page.choose_output_dir,
        "选择结果输出目录",
    )
    left_column.addWidget(page.save_box)

    controls = QHBoxLayout()
    page.start_det_btn = QPushButton("开始检测")
    page.start_det_btn.clicked.connect(page.start_detection)
    page.stop_det_btn = QPushButton("停止")
    page.stop_det_btn.setObjectName("softButton")
    page.stop_det_btn.setEnabled(False)
    page.stop_det_btn.clicked.connect(page.stop_detection)
    controls.addWidget(page.start_det_btn)
    controls.addWidget(page.stop_det_btn)
    left_column.addLayout(controls)
    page.open_val_save_btn = QPushButton("打开保存目录")
    page.open_val_save_btn.setObjectName("softButton")
    page.open_val_save_btn.clicked.connect(page.open_detection_save_dir)
    page.open_val_save_btn.setVisible(False)
    left_column.addWidget(page.open_val_save_btn)
    page.detect_log = QTextEdit()
    page.prepare_readonly_text(page.detect_log)
    page.detect_log.setMinimumHeight(180)
    left_column.addWidget(page.detect_log, 1)
    for field_box in (
        model_box,
        page.conf_box,
        page.iou_box,
        page.imgsz_box,
        page.mode_box,
        page.source_box,
        page.data_box,
        page.source_scope_box,
        page.camera_box,
        page.save_box,
    ):
        field_box.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Fixed,
        )
    split.addWidget(left_shell)

    right = QVBoxLayout()
    right.setContentsMargins(0, 0, 0, 0)
    page.toolbar_widget = QWidget()
    toolbar = QHBoxLayout(page.toolbar_widget)
    toolbar.setContentsMargins(0, 0, 0, 0)
    page.result_nav_widget = QWidget()
    nav_toolbar = QHBoxLayout(page.result_nav_widget)
    nav_toolbar.setContentsMargins(0, 0, 0, 0)
    nav_toolbar.addWidget(QLabel("批量检测结果"))
    for text, slot in [
        ("上一张", page.prev_result),
        ("下一张", page.next_result),
        ("第一张", page.first_result),
        ("最后一张", page.last_result),
        ("列表", page.show_result_list),
        ("打开保存文件夹", page.open_detection_save_dir),
    ]:
        button = QPushButton(text)
        button.setObjectName("softButton")
        button.clicked.connect(slot)
        nav_toolbar.addWidget(button)
        if text != "打开保存文件夹":
            page.result_nav_buttons.append(button)
    page.counter = QLabel("0/0")
    nav_toolbar.addWidget(page.counter)
    nav_toolbar.addStretch(1)
    toolbar.addWidget(page.result_nav_widget, 1)
    page.video_progress_widget = QWidget()
    video_toolbar = QHBoxLayout(page.video_progress_widget)
    video_toolbar.setContentsMargins(0, 0, 0, 0)
    page.video_play_btn = QPushButton()
    page.video_play_btn.setObjectName("softButton")
    page.video_play_btn.setIcon(
        page.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
    )
    page.video_play_btn.setToolTip("播放视频")
    page.video_play_btn.setCheckable(True)
    page.video_play_btn.setMinimumWidth(36)
    page.video_play_btn.toggled.connect(page.toggle_video_playback)
    video_toolbar.addWidget(page.video_play_btn)
    page.video_progress = QSlider(Qt.Orientation.Horizontal)
    page.video_progress.setObjectName("videoProgress")
    page.video_progress.setRange(0, 1000)
    page.video_progress.setValue(0)
    video_toolbar.addWidget(page.video_progress, 1)
    page.video_progress_label = QLabel("0%")
    page.video_progress_label.setMinimumWidth(42)
    video_toolbar.addWidget(page.video_progress_label)
    page.video_progress.valueChanged.connect(
        lambda value: page.video_progress_label.setText(f"{int(value) / 10:.0f}%")
    )
    page.video_prev_btn = QPushButton("上个视频")
    page.video_prev_btn.setObjectName("softButton")
    page.video_prev_btn.clicked.connect(page.previous_video)
    video_toolbar.addWidget(page.video_prev_btn)
    page.video_next_btn = QPushButton("下个视频")
    page.video_next_btn.setObjectName("softButton")
    page.video_next_btn.clicked.connect(page.next_video)
    video_toolbar.addWidget(page.video_next_btn)
    page.video_list_btn = QPushButton("列表")
    page.video_list_btn.setObjectName("softButton")
    page.video_list_btn.clicked.connect(page.show_result_list)
    video_toolbar.addWidget(page.video_list_btn)
    page.video_open_dir_btn = QPushButton("打开保存文件夹")
    page.video_open_dir_btn.setObjectName("softButton")
    page.video_open_dir_btn.clicked.connect(page.open_detection_save_dir)
    video_toolbar.addWidget(page.video_open_dir_btn)
    page.video_progress_widget.setVisible(False)
    toolbar.addWidget(page.video_progress_widget, 1)
    right.addWidget(page.toolbar_widget)
    page.views_widget = QWidget()
    page.views_widget.setMinimumWidth(0)
    page.views_widget.setSizePolicy(
        QSizePolicy.Policy.Expanding,
        QSizePolicy.Policy.Expanding,
    )
    views = QHBoxLayout(page.views_widget)
    views.setContentsMargins(0, 0, 0, 0)
    source_panel = QWidget()
    source_panel.setObjectName("validationPreviewPanel")
    source_panel.setMinimumWidth(0)
    source_panel.setSizePolicy(
        QSizePolicy.Policy.Ignored,
        QSizePolicy.Policy.Expanding,
    )
    source_panel_layout = QVBoxLayout(source_panel)
    source_panel_layout.setContentsMargins(0, 0, 0, 0)
    source_panel_layout.setSpacing(0)
    page.source_view = ImageView("源图")
    page.source_view.setMinimumWidth(0)
    page.source_view.setSizePolicy(
        QSizePolicy.Policy.Ignored,
        QSizePolicy.Policy.Expanding,
    )
    source_panel_layout.addWidget(page.source_view, 1)
    page.source_video_player = VideoPlayer("源视频")
    source_panel_layout.addWidget(page.source_video_player, 1)
    page.source_video_player.hide()
    result_panel = QWidget()
    result_panel.setObjectName("validationPreviewPanel")
    result_panel.setMinimumWidth(0)
    result_panel.setSizePolicy(
        QSizePolicy.Policy.Ignored,
        QSizePolicy.Policy.Expanding,
    )
    result_panel_layout = QVBoxLayout(result_panel)
    result_panel_layout.setContentsMargins(0, 0, 0, 0)
    result_panel_layout.setSpacing(0)
    page.result_view = ImageView("检测结果图")
    page.result_view.setMinimumWidth(0)
    page.result_view.setSizePolicy(
        QSizePolicy.Policy.Ignored,
        QSizePolicy.Policy.Expanding,
    )
    result_panel_layout.addWidget(page.result_view, 1)
    page.result_video_player = VideoPlayer("检测后视频")
    result_panel_layout.addWidget(page.result_video_player, 1)
    page.result_video_player.hide()
    page.video_playback = VideoPlaybackController(
        page.source_video_player,
        page.result_video_player,
        page.video_progress,
    )
    page.source_video_player.player.playbackStateChanged.connect(
        page.handle_video_playback_state
    )
    page.source_video_player.player.mediaStatusChanged.connect(
        page.handle_video_media_status
    )
    page.source_panel = source_panel
    page.source_panel_layout = source_panel_layout
    page.result_panel = result_panel
    page.result_panel_layout = result_panel_layout
    views.addWidget(source_panel, 1)
    views.addWidget(result_panel, 1)
    views.setStretch(0, 1)
    views.setStretch(1, 1)
    right.addWidget(page.views_widget, 2)
    page.table_panel = Card("检测结果详情表")
    page.table = QTableWidget(0, 5)
    page.table.setHorizontalHeaderLabels(
        ["类别", "置信度", "坐标(x,y)", "尺寸(w×h)", "角度"]
    )
    page.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    page.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    page.table_panel.layout.addWidget(page.table)
    right.addWidget(page.table_panel, 1)
    page.val_log_panel = Card("验证日志")
    page.val_log = QTextEdit()
    page.prepare_readonly_text(page.val_log)
    page.val_log_panel.layout.addWidget(page.val_log, 1)
    page.val_log.setMinimumHeight(220)
    right.addWidget(page.val_log_panel, 1)
    right_widget = QWidget()
    right_widget.setLayout(right)
    page.validation_right_layout = right
    page.validation_views_layout = views
    split.addWidget(right_widget)
    split.setStretch(0, 1)
    split.setStretch(1, 3)


