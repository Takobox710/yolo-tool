from __future__ import annotations

from src.shared.qt import QHBoxLayout, QProgressBar, QPushButton, QSizePolicy, QVBoxLayout, QWidget
from src.ui.features.data.model_export.controls import configure_field_box
from src.ui.features.data.model_export.layout_primitives import (
    _checkbox,
    _double_spin_field,
    _section_box,
    _spin_field,
)


def build_format_options(page, settings) -> None:
    spin_field = _spin_field
    double_spin_field = _double_spin_field
    section_box = _section_box
    checkbox = _checkbox

    page.simplify_box, page.simplify_check = page.checkbox_with_help(
        "简化 ONNX", settings.simplify, "导出后使用 ONNXSlim 简化 ONNX 图。"
    )
    page.onnx_simplify_btn = page.simplify_check
    page.opset_box, page.opset_spin = spin_field(
        page, "ONNX opset", settings.opset or 0, 0, 21, "设为 0 表示使用后端默认 opset。"
    )
    page.onnx_opset_box = page.opset_box
    page.onnx_opset_spin = page.opset_spin
    page.workspace_box, page.workspace_spin = double_spin_field(
        page, "TensorRT workspace (GB)", settings.workspace if settings.workspace is not None else 4.0,
        0.0, 1024.0, 0.5, "TensorRT 工作空间上限。",
    )
    page.optimize_box, page.optimize_check = page.checkbox_with_help(
        "TorchScript 优化", settings.optimize, "仅传给 TorchScript 导出器。"
    )

    page.basic_options_box, basic_layout = section_box(None, "modelExportBasicSection")
    basic_layout.setHorizontalSpacing(12)
    basic_layout.setVerticalSpacing(8)
    for index in range(4):
        basic_layout.setColumnStretch(index, 1)
    page.basic_format_box = QWidget()
    basic_format_layout = QVBoxLayout(page.basic_format_box)
    basic_format_layout.setContentsMargins(0, 0, 0, 0)
    basic_format_layout.setSpacing(0)
    basic_format_layout.addWidget(page.simplify_box)
    basic_format_layout.addWidget(page.optimize_box)
    page.basic_format_box.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
    page.basic_format_box.setMinimumWidth(0)
    for option_box, check in ((page.simplify_box, page.simplify_check), (page.optimize_box, page.optimize_check)):
        option_box.setMinimumWidth(0)
        option_box.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        check.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    page.basic_options_grid = basic_layout

    page.inference_format_box = QWidget()
    inference_format_layout = QVBoxLayout(page.inference_format_box)
    inference_format_layout.setContentsMargins(0, 0, 0, 0)
    inference_format_layout.setSpacing(8)
    inference_format_layout.addWidget(page.opset_box)
    inference_format_layout.addWidget(page.workspace_box)
    page.inference_format_box.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
    page.inference_grid.addWidget(page.inference_format_box, 2, 1)

    page.dynamic_box, dynamic_layout = section_box(None, "modelExportDynamicSection")
    dynamic_layout.setHorizontalSpacing(12)
    dynamic_layout.setVerticalSpacing(8)
    for index in range(3):
        dynamic_layout.setColumnStretch(index, 1)
    page.dynamic_input_check = checkbox(page, "动态输入", False, "统一控制非 ONNX 格式的动态输入。")
    page.dynamic_batch_check = checkbox(page, "动态 Batch", settings.dynamic_batch, "允许导出模型接受动态 Batch。")
    page.dynamic_height_check = checkbox(page, "动态高度", settings.dynamic_height, "允许导出模型接受动态高度。")
    page.dynamic_width_check = checkbox(page, "动态宽度", settings.dynamic_width, "允许导出模型接受动态宽度。")
    page.onnx_dynamic_batch_check = checkbox(page, "动态 Batch", settings.dynamic_batch, "允许导出的 ONNX 接受动态 Batch。")
    page.onnx_dynamic_size_check = checkbox(page, "动态宽高", settings.dynamic_height or settings.dynamic_width, "同时允许导出的 ONNX 接受动态宽度和动态高度。")
    page.onnx_dynamic_row = QHBoxLayout()
    page.onnx_dynamic_row.setContentsMargins(0, 0, 0, 0)
    page.onnx_dynamic_row.setSpacing(8)
    page.onnx_dynamic_row.addWidget(page.onnx_dynamic_batch_check, 1)
    page.onnx_dynamic_row.addWidget(page.onnx_dynamic_size_check, 1)
    dynamic_layout.addWidget(page.dynamic_batch_check, 0, 0)
    dynamic_layout.addWidget(page.dynamic_height_check, 0, 1)
    dynamic_layout.addWidget(page.dynamic_width_check, 0, 2)
    dynamic_layout.addLayout(page.onnx_dynamic_row, 1, 0, 1, 3)
    page.dynamic_box.setToolTip("按格式控制动态输入；SAM2、NCNN 不使用动态轴。")

    page.nms_box = QWidget()
    page.nms_box.setObjectName("modelExportNmsSection")
    page.nms_box.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
    nms_layout = QHBoxLayout(page.nms_box)
    nms_layout.setContentsMargins(0, 0, 0, 0)
    nms_layout.setSpacing(12)
    page.nms_layout = nms_layout
    page.nms_check = checkbox(page, "导出 NMS", settings.nms, "仅对支持内置 NMS 的 YOLO 导出格式生效。")
    page.agnostic_nms_check = checkbox(page, "类别无关", settings.agnostic_nms, "NMS 是否忽略类别执行抑制。")
    page.onnx_nms_btn = page.nms_check
    page.onnx_agnostic_btn = page.agnostic_nms_check
    page.nms_box.setMinimumWidth(0)
    page.nms_check.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
    nms_layout.addWidget(page.nms_check)
    page.basic_option_row = QWidget()
    basic_option_layout = QHBoxLayout(page.basic_option_row)
    basic_option_layout.setContentsMargins(0, 0, 0, 0)
    basic_option_layout.setSpacing(12)
    basic_option_layout.addWidget(page.basic_format_box)
    basic_option_layout.addWidget(page.nms_box)
    basic_option_layout.addWidget(page.agnostic_nms_check)
    basic_option_layout.addWidget(page.dynamic_input_check)
    basic_option_layout.addStretch(1)
    page.agnostic_nms_check.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
    page.dynamic_input_check.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
    for index in range(4):
        basic_option_layout.setStretch(index, 1)
    page.basic_options_grid.addWidget(page.basic_option_row, 0, 0, 1, 4)

    page.int8_box, int8_layout = section_box("INT8 校准与验证", "modelExportInt8Section")
    int8_layout.setHorizontalSpacing(12)
    int8_layout.setVerticalSpacing(8)
    int8_layout.setColumnStretch(0, 1)
    int8_layout.setColumnStretch(1, 1)
    page.calibration_data_box, page.calibration_data_edit = page.field(
        "校准数据", page.display_path(settings.calibration_data), page.choose_calibration_data,
        "dataset.yaml 或图片目录", "INT8 校准数据可直接选择 dataset.yaml 或图片目录。",
    )
    page.calibration_samples_box, page.calibration_samples_spin = spin_field(
        page, "校准样本数", settings.calibration_samples, 1, 100000, "校准集使用的最大图片数量。"
    )
    page.calibration_pack_btn = QPushButton("获取通用校准集")
    page.calibration_pack_btn.setToolTip("下载并缓存一套公开的通用图片，作为无需项目数据的 INT8 校准集。")
    page.calibration_pack_btn.clicked.connect(page.download_generic_calibration_pack)
    page.calibration_pack_progress = QProgressBar()
    page.calibration_pack_progress.setRange(0, 100)
    page.calibration_pack_progress.setValue(0)
    page.calibration_pack_progress.setFormat("下载通用校准集 %p%")
    page.calibration_pack_progress.setVisible(False)
    page.validate_quantized_box, page.validate_quantized_check = page.checkbox_with_help(
        "量化后验证", settings.validate_quantized, "使用 ONNX Runtime 执行前向冒烟验证，检查输入输出、形状和有限数值。"
    )
    page.validation_samples_box, page.validation_samples_spin = spin_field(
        page, "验证样本数", settings.validation_samples, 1, 100000, "量化后冒烟验证的最大图片数量。"
    )
    for box in (page.calibration_data_box, page.calibration_samples_box, page.validation_samples_box):
        configure_field_box(box)
    int8_layout.addWidget(page.calibration_data_box, 0, 0, 1, 2)
    int8_layout.addWidget(page.calibration_samples_box, 1, 0)
    int8_layout.addWidget(page.calibration_pack_btn, 1, 1)
    int8_layout.addWidget(page.calibration_pack_progress, 2, 0, 1, 2)
    int8_layout.addWidget(page.validate_quantized_box, 3, 0)
    int8_layout.addWidget(page.validation_samples_box, 3, 1)

    source_layout = page.source_card.layout
    source_layout.addWidget(page.basic_options_box)
    source_layout.addStretch(1)
    source_layout.insertStretch(0, 1)
    source_layout.insertStretch(2, 1)
    source_layout.insertStretch(4, 1)
    page.inference_card.layout.addWidget(page.dynamic_box)
    page.inference_card.layout.addWidget(page.int8_box)
    page.inference_card.layout.addStretch(1)
