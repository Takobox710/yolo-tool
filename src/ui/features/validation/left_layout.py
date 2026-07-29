from __future__ import annotations

from pathlib import Path

from src.services.data_ops import relative_path_from_project, resolve_project_path
from src.services.validation import VIDEO_SUFFIXES, is_live_source_mode
from src.ui.shared.page_base import Card
from src.shared.qt import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QTextEdit
from src.ui.features.validation.sources import IMAGE_SOURCE_OPTIONS, SOURCE_SCOPE_OPTIONS, VIDEO_SOURCE_OPTIONS


def build_validation_left_layout(page, context, split) -> None:
    left_shell = Card()
    page.left_shell = left_shell
    left_column = left_shell.layout
    page.left_column_layout = left_column
    validation = context.settings.validation
    stored_mode = validation.source_mode
    if is_live_source_mode(stored_mode):
        stored_mode = "摄像头检测"
        validation.source_mode = stored_mode
    stored_source_path = validation.source_path
    if stored_mode in {"图片检测", "视频检测", "图片文件夹", "视频文件夹", "图片/视频文件夹", "图片/视频"}:
        resolved_source = Path(resolve_project_path(stored_source_path, page.project_root())) if stored_source_path else None
        if stored_mode in {"视频检测", "视频文件夹"}:
            stored_mode = "视频检测"
        elif stored_mode == "图片/视频" and resolved_source is not None:
            stored_mode = "视频检测" if resolved_source.suffix.lower() in VIDEO_SUFFIXES else "图片检测"
            if resolved_source.is_file():
                stored_source_path = str(resolved_source.parent)
        else:
            stored_mode = "视频检测" if stored_mode in {"视频检测", "视频文件夹"} else "图片检测"
        validation.source_mode = stored_mode
        validation.source_path = stored_source_path

    model_title = QLabel("模型配置")
    model_title.setObjectName("sectionTitle")
    model_title.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    left_column.addWidget(model_title)
    model_box, page.model_combo = page.stacked_combo_field("选择模型", "", [], browse=lambda combo: page._choose_pt_for_combo(combo), placeholder="选择或输入模型路径")
    page.model_combo.setMinimumWidth(140)
    left_column.addWidget(model_box)
    conf_row = QHBoxLayout()
    page.conf_box, page.conf_edit = page.field("置信度", str(validation.confidence), placeholder="例如 0.25")
    page.iou_box, page.iou_edit = page.field("IoU", str(validation.iou), placeholder="例如 0.45")
    page.imgsz_box, page.imgsz_combo = page.combo_field("图片尺寸", str(validation.imgsz), ["640", "960", "1280"], editable=True, placeholder="例如 640")
    page.imgsz_combo.setMinimumContentsLength(5)
    for widget in (page.conf_box, page.iou_box, page.imgsz_box):
        conf_row.addWidget(widget)
    left_column.addLayout(conf_row)
    page.mode_box, page.mode_combo = page.combo_field("检测模式", stored_mode, ["图片检测", "视频检测", "摄像头检测", "数据集验证"])
    left_column.addWidget(page.mode_box)
    initial_source_text = relative_path_from_project(validation.source_path, page.project_root()) if validation.source_path else (validation.source_selection or validation.source_scope)
    initial_source_options = VIDEO_SOURCE_OPTIONS if stored_mode == "视频检测" else IMAGE_SOURCE_OPTIONS
    page.source_box, page.source_combo = page.stacked_combo_field("输入源", initial_source_text, initial_source_options, browse=lambda combo: page.choose_detection_source(combo), placeholder="选择输入文件夹")
    left_column.addWidget(page.source_box)
    page.data_box, page.data_edit = page.path_field("数据集 YAML", validation.data, page.choose_dataset_yaml, "选择 data.yaml")
    left_column.addWidget(page.data_box)
    page.source_scope_box, page.source_scope_combo = page.stacked_combo_field("选择验证源", validation.source_scope, SOURCE_SCOPE_OPTIONS, browse=lambda combo: page.choose_validation_source(combo), placeholder="选择或输入验证文件夹")
    left_column.addWidget(page.source_scope_box)
    page.camera_box, page.camera_combo = page.combo_field("摄像头", str(validation.camera_index), ["0", "1", "2", "3"])
    left_column.addWidget(page.camera_box)
    page.save_box, page.save_edit = page.path_field("输出文件夹", validation.save_dir, page.choose_output_dir, "选择结果输出目录")
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
    for field_box in (model_box, page.conf_box, page.iou_box, page.imgsz_box, page.mode_box, page.source_box, page.data_box, page.source_scope_box, page.camera_box, page.save_box):
        field_box.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    split.addWidget(left_shell)


__all__ = ["build_validation_left_layout"]
