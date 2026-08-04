from __future__ import annotations

from src.services.model_export import export_display_names, resolve_export_format
from src.services.runtime.variant import CPU_VARIANT, installed_variant
from src.shared.qt import QDoubleSpinBox, QGridLayout, QHBoxLayout, QLineEdit, QSpinBox, QTextEdit, QVBoxLayout, QWidget
from src.ui.features.data.model_export.controls import configure_field_box as _configure_field_box, spin_control_field as _spin_control_field
from src.ui.features.data.model_export.layout_primitives import _spin_field
from src.ui.shared.page_base import Card


def build_model_export_layout(page) -> None:
    settings = page.context.settings.model_export
    root_layout = QVBoxLayout(page)
    root_layout.setContentsMargins(12, 12, 12, 12)
    root_layout.setSpacing(10)
    _build_fixed_fields(page, settings)
    from src.ui.features.data.model_export.layout_options import build_format_options

    build_format_options(page, settings)
    root_layout.addWidget(page.onnx_top_box)
    from src.ui.features.data.model_export.layout_actions import build_action_row

    build_action_row(page, root_layout)
    page.log = QTextEdit()
    page.prepare_readonly_text(page.log)
    page.log.setAcceptDrops(False)
    page.log.setPlaceholderText("预览或转换后将在这里显示环境、目标路径和运行日志。")
    root_layout.addWidget(page.log, 1)
    for widget in (page.model_combo, page.output_edit, page.imgsz_edit, page.calibration_data_edit):
        widget.setAcceptDrops(False)
    page.onnx_top_box.setVisible(True)
    page.legacy_top_box.setVisible(True)


def _build_fixed_fields(page, settings) -> None:
    page.model_box, page.model_combo = page.stacked_combo_field("源模型", page._model_display_path(settings.model_path), [], page.choose_model, "选择 .pt 模型", "YOLO 模型和可识别的 SAM2/SAM2.1 checkpoint 使用同一个导出入口。")
    page.output_box, page.output_edit = page.path_field("输出目录", settings.output_dir, page.choose_dir, "选择模型转换结果目录")
    format_names = export_display_names(include_engine=installed_variant() != CPU_VARIANT)
    selected_format = resolve_export_format(settings.format).display_name
    if selected_format not in format_names:
        selected_format = format_names[0]
    page.format_box, page.format_combo = page.combo_field("目标格式", selected_format, format_names)
    page.precision_box, page.precision_combo = page.combo_field("导出精度", _precision_label(settings.precision), ["FP32", "FP16", "INT8"], help_text="精度、图简化、动态轴和 NMS 是相互独立的配置。")
    page.imgsz_box, page.imgsz_edit = _text_field(page, "输入尺寸", str(settings.imgsz), placeholder="例如 640", help_text="SAM2/SAM2.1 固定使用 1024；其他格式使用 YOLO 输入尺寸。")
    page.batch_box, page.batch_spin = _spin_field(page, "Batch", settings.batch, 1, 1024, "导出 batch；SAM2 固定为 1。")
    page.conf_spin = _double_spin(settings.nms_conf, "Conf", "NMS 置信度阈值；不支持 NMS 的格式会保留该值但不会传入命令。")
    page.iou_spin = _double_spin(settings.nms_iou, "IoU", "NMS IoU 阈值；不支持 NMS 的格式会保留该值但不会传入命令。")
    page.max_det_spin = QSpinBox()
    page.max_det_spin.setRange(1, 100000)
    page.max_det_spin.setValue(settings.nms_max_det)
    page.conf_box = _spin_control_field("Conf", page.conf_spin)
    page.iou_box = _spin_control_field("IoU", page.iou_spin)
    page.max_det_box = _spin_control_field("最大检测数", page.max_det_spin)
    page.nms_conf_spin = page.conf_spin
    page.nms_iou_spin = page.iou_spin
    page.nms_max_det_spin = page.max_det_spin
    page.onnx_conf_spin = page.conf_spin
    page.onnx_iou_spin = page.iou_spin
    page.onnx_max_det_spin = page.max_det_spin
    page.onnx_conf_box = page.conf_box
    page.onnx_iou_box = page.iou_box
    page.onnx_max_det_box = page.max_det_box
    for box in (page.model_box, page.output_box, page.format_box, page.precision_box, page.imgsz_box, page.batch_box, page.conf_box, page.iou_box, page.max_det_box):
        _configure_field_box(box)
    source_grid = QGridLayout()
    source_grid.setContentsMargins(0, 0, 0, 0)
    source_grid.setHorizontalSpacing(12)
    source_grid.setVerticalSpacing(10)
    source_grid.setColumnStretch(0, 1)
    source_grid.setColumnStretch(1, 1)
    source_grid.addWidget(page.model_box, 0, 0)
    source_grid.addWidget(page.output_box, 0, 1)
    source_grid.addWidget(page.format_box, 1, 0)
    source_grid.addWidget(page.precision_box, 1, 1)
    page.source_grid = source_grid
    page.onnx_source_grid = source_grid
    page.source_card = Card("基础配置")
    page.source_card.layout.addLayout(source_grid)
    inference_grid = QGridLayout()
    inference_grid.setContentsMargins(0, 0, 0, 0)
    inference_grid.setHorizontalSpacing(12)
    inference_grid.setVerticalSpacing(10)
    inference_grid.setColumnStretch(0, 1)
    inference_grid.setColumnStretch(1, 1)
    inference_grid.addWidget(page.imgsz_box, 0, 0)
    inference_grid.addWidget(page.batch_box, 0, 1)
    inference_grid.addWidget(page.conf_box, 1, 0)
    inference_grid.addWidget(page.iou_box, 1, 1)
    inference_grid.addWidget(page.max_det_box, 2, 0)
    page.onnx_param_grid = inference_grid
    page.inference_grid = inference_grid
    page.onnx_param_first_row = 0
    page.onnx_param_second_row = 1
    page.onnx_param_third_row = 2
    page.inference_card = Card("推理参数")
    page.inference_card.layout.addLayout(inference_grid)
    page.onnx_param_title = page.inference_card.layout.itemAt(0).widget()
    page.onnx_right_card = page.inference_card
    top_box = QWidget()
    top_layout = QHBoxLayout()
    top_layout.setContentsMargins(0, 0, 0, 0)
    top_layout.setSpacing(16)
    top_layout.addWidget(page.source_card, 3)
    top_layout.addWidget(page.inference_card, 2)
    top_box.setLayout(top_layout)
    page.onnx_top_layout = top_layout
    page.onnx_top_box = top_box
    page.legacy_top_box = top_box


def _text_field(page, label: str, value: str, *, placeholder: str = "", help_text: str = ""):
    box = QWidget()
    layout = QVBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    caption_box, _caption, _icon = page._caption_widget(label, help_text=help_text)
    edit = QLineEdit(str(value))
    edit.setObjectName("modelExportFlatEdit")
    edit.setPlaceholderText(placeholder)
    edit.setMinimumWidth(0)
    edit.setFixedHeight(23)
    layout.addWidget(caption_box)
    layout.addWidget(edit)
    return box, edit


def _double_spin(value: float, label: str, help_text: str) -> QDoubleSpinBox:
    spin = QDoubleSpinBox()
    spin.setRange(0.0, 1.0)
    spin.setDecimals(3)
    spin.setSingleStep(0.05)
    spin.setValue(float(value))
    spin.setToolTip(help_text)
    spin.setObjectName(f"modelExport{label.replace(' ', '')}Spin")
    return spin


def _precision_label(value: str) -> str:
    return {"fp16": "FP16", "int8": "INT8"}.get(str(value).lower(), "FP32")


__all__ = ["build_model_export_layout"]
