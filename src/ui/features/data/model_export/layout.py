from __future__ import annotations

from src.services.model_export import export_display_names, resolve_export_format
from src.services.runtime.variant import CPU_VARIANT, installed_variant
from src.shared.qt import (
    QCheckBox,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from src.ui.features.data.model_export.controls import (
    configure_field_box as _configure_field_box,
    section_box as _section_box,
    spin_control_field as _spin_control_field,
)
from src.ui.shared.page_base import Card


def build_model_export_layout(page) -> None:
    settings = page.context.settings.model_export
    root_layout = QVBoxLayout(page)
    root_layout.setContentsMargins(12, 12, 12, 12)
    root_layout.setSpacing(10)

    _build_fixed_fields(page, settings)
    _build_format_options(page, settings)

    root_layout.addWidget(page.onnx_top_box)

    _build_action_row(page, root_layout)

    page.log = QTextEdit()
    page.prepare_readonly_text(page.log)
    page.log.setAcceptDrops(False)
    page.log.setPlaceholderText("预览或转换后将在这里显示环境、目标路径和运行日志。")
    root_layout.addWidget(page.log, 1)

    for widget in (
        page.model_combo,
        page.output_edit,
        page.imgsz_edit,
        page.calibration_data_edit,
    ):
        widget.setAcceptDrops(False)

    page.onnx_top_box.setVisible(True)
    page.legacy_top_box.setVisible(True)


def _build_fixed_fields(page, settings) -> None:
    page.model_box, page.model_combo = page.stacked_combo_field(
        "源模型",
        page._model_display_path(settings.model_path),
        [],
        page.choose_model,
        "选择 .pt 模型",
        "YOLO 模型和可识别的 SAM2/SAM2.1 checkpoint 使用同一个导出入口。",
    )
    page.output_box, page.output_edit = page.path_field(
        "输出目录", settings.output_dir, page.choose_dir, "选择模型转换结果目录"
    )
    format_names = export_display_names(include_engine=installed_variant() != CPU_VARIANT)
    selected_format = resolve_export_format(settings.format).display_name
    if selected_format not in format_names:
        selected_format = format_names[0]
    page.format_box, page.format_combo = page.combo_field(
        "目标格式",
        selected_format,
        format_names,
    )
    page.precision_box, page.precision_combo = page.combo_field(
        "导出精度",
        _precision_label(settings.precision),
        ["FP32", "FP16", "INT8"],
        help_text="精度、图简化、动态轴和 NMS 是相互独立的配置。",
    )
    page.imgsz_box, page.imgsz_edit = _text_field(
        page,
        "输入尺寸",
        str(settings.imgsz),
        placeholder="例如 640",
        help_text="SAM2/SAM2.1 固定使用 1024；其他格式使用 YOLO 输入尺寸。",
    )
    page.batch_box, page.batch_spin = _spin_field(
        page, "Batch", settings.batch, 1, 1024, "导出 batch；SAM2 固定为 1。"
    )

    page.conf_spin = _double_spin(
        settings.nms_conf,
        "Conf",
        "NMS 置信度阈值；不支持 NMS 的格式会保留该值但不会传入命令。",
    )
    page.iou_spin = _double_spin(
        settings.nms_iou,
        "IoU",
        "NMS IoU 阈值；不支持 NMS 的格式会保留该值但不会传入命令。",
    )
    page.max_det_spin = QSpinBox()
    page.max_det_spin.setRange(1, 100000)
    page.max_det_spin.setValue(settings.nms_max_det)
    page.conf_box = _spin_control_field("Conf", page.conf_spin)
    page.iou_box = _spin_control_field("IoU", page.iou_spin)
    page.max_det_box = _spin_control_field("最大检测数", page.max_det_spin)

    # Keep the old attribute names as compatibility aliases for existing page hooks.
    page.nms_conf_spin = page.conf_spin
    page.nms_iou_spin = page.iou_spin
    page.nms_max_det_spin = page.max_det_spin
    page.onnx_conf_spin = page.conf_spin
    page.onnx_iou_spin = page.iou_spin
    page.onnx_max_det_spin = page.max_det_spin
    page.onnx_conf_box = page.conf_box
    page.onnx_iou_box = page.iou_box
    page.onnx_max_det_box = page.max_det_box

    for box in (
        page.model_box,
        page.output_box,
        page.format_box,
        page.precision_box,
        page.imgsz_box,
        page.batch_box,
        page.conf_box,
        page.iou_box,
        page.max_det_box,
    ):
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

    source_card = Card("基础配置")
    source_card.layout.addLayout(source_grid)
    page.source_card = source_card

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
    top_layout = _top_row_layout(page.source_card, page.inference_card)
    top_box.setLayout(top_layout)
    page.onnx_top_layout = top_layout
    page.onnx_top_box = top_box
    page.legacy_top_box = top_box


def _build_format_options(page, settings) -> None:
    page.simplify_box, page.simplify_check = page.checkbox_with_help(
        "简化 ONNX", settings.simplify, "导出后使用 ONNXSlim 简化 ONNX 图。"
    )
    page.onnx_simplify_btn = page.simplify_check

    page.opset_box, page.opset_spin = _spin_field(
        page, "ONNX opset", settings.opset or 0, 0, 21, "设为 0 表示使用后端默认 opset。"
    )
    page.onnx_opset_box = page.opset_box
    page.onnx_opset_spin = page.opset_spin

    page.workspace_box, page.workspace_spin = _double_spin_field(
        page,
        "TensorRT workspace (GB)",
        settings.workspace if settings.workspace is not None else 4.0,
        0.0,
        1024.0,
        0.5,
        "TensorRT 工作空间上限。",
    )
    page.optimize_box, page.optimize_check = page.checkbox_with_help(
        "TorchScript 优化", settings.optimize, "仅传给 TorchScript 导出器。"
    )

    page.basic_options_box, basic_layout = _section_box(
        None, "modelExportBasicSection"
    )
    basic_layout.setHorizontalSpacing(12)
    basic_layout.setVerticalSpacing(8)
    basic_layout.setColumnStretch(0, 1)
    basic_layout.setColumnStretch(1, 1)
    basic_layout.setColumnStretch(2, 1)
    basic_layout.setColumnStretch(3, 1)
    page.basic_format_box = QWidget()
    basic_format_layout = QVBoxLayout(page.basic_format_box)
    basic_format_layout.setContentsMargins(0, 0, 0, 0)
    basic_format_layout.setSpacing(0)
    basic_format_layout.addWidget(page.simplify_box)
    basic_format_layout.addWidget(page.optimize_box)
    page.basic_format_box.setSizePolicy(
        QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
    )
    page.basic_format_box.setMinimumWidth(0)
    for option_box, check in (
        (page.simplify_box, page.simplify_check),
        (page.optimize_box, page.optimize_check),
    ):
        option_box.setMinimumWidth(0)
        option_box.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        check.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    page.basic_options_grid = basic_layout

    page.inference_format_box = QWidget()
    inference_format_layout = QVBoxLayout(page.inference_format_box)
    inference_format_layout.setContentsMargins(0, 0, 0, 0)
    inference_format_layout.setSpacing(8)
    inference_format_layout.addWidget(page.opset_box)
    inference_format_layout.addWidget(page.workspace_box)
    page.inference_format_box.setSizePolicy(
        QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
    )
    page.inference_grid.addWidget(page.inference_format_box, 2, 1)

    page.dynamic_box, dynamic_layout = _section_box(
        None, "modelExportDynamicSection"
    )
    dynamic_layout.setHorizontalSpacing(12)
    dynamic_layout.setVerticalSpacing(8)
    dynamic_layout.setColumnStretch(0, 1)
    dynamic_layout.setColumnStretch(1, 1)
    dynamic_layout.setColumnStretch(2, 1)
    page.dynamic_input_check = _checkbox(
        page, "动态输入", False, "统一控制非 ONNX 格式的动态输入。"
    )
    page.dynamic_batch_check = _checkbox(
        page, "动态 Batch", settings.dynamic_batch, "允许导出模型接受动态 Batch。"
    )
    page.dynamic_height_check = _checkbox(
        page, "动态高度", settings.dynamic_height, "允许导出模型接受动态高度。"
    )
    page.dynamic_width_check = _checkbox(
        page, "动态宽度", settings.dynamic_width, "允许导出模型接受动态宽度。"
    )
    page.onnx_dynamic_batch_check = _checkbox(
        page, "动态 Batch", settings.dynamic_batch, "允许导出的 ONNX 接受动态 Batch。"
    )
    page.onnx_dynamic_size_check = _checkbox(
        page,
        "动态宽高",
        settings.dynamic_height or settings.dynamic_width,
        "同时允许导出的 ONNX 接受动态宽度和动态高度。",
    )
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
    page.nms_box.setSizePolicy(
        QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
    )
    nms_layout = QHBoxLayout(page.nms_box)
    nms_layout.setContentsMargins(0, 0, 0, 0)
    nms_layout.setSpacing(12)
    page.nms_layout = nms_layout
    page.nms_check = _checkbox(
        page, "导出 NMS", settings.nms, "仅对支持内置 NMS 的 YOLO 导出格式生效。"
    )
    page.agnostic_nms_check = _checkbox(
        page, "类别无关", settings.agnostic_nms, "NMS 是否忽略类别执行抑制。"
    )
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
    page.agnostic_nms_check.setSizePolicy(
        QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
    )
    page.dynamic_input_check.setSizePolicy(
        QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
    )
    for index in range(4):
        basic_option_layout.setStretch(index, 1)
    page.basic_options_grid.addWidget(page.basic_option_row, 0, 0, 1, 4)

    page.int8_box, int8_layout = _section_box(
        "INT8 校准与验证", "modelExportInt8Section"
    )
    int8_layout.setHorizontalSpacing(12)
    int8_layout.setVerticalSpacing(8)
    int8_layout.setColumnStretch(0, 1)
    int8_layout.setColumnStretch(1, 1)
    page.calibration_data_box, page.calibration_data_edit = page.field(
        "校准数据",
        page.display_path(settings.calibration_data),
        page.choose_calibration_data,
        "dataset.yaml 或图片目录",
        "INT8 校准数据可直接选择 dataset.yaml 或图片目录。",
    )
    page.calibration_samples_box, page.calibration_samples_spin = _spin_field(
        page,
        "校准样本数",
        settings.calibration_samples,
        1,
        100000,
        "校准集使用的最大图片数量。",
    )
    page.calibration_pack_btn = QPushButton("获取通用校准集")
    page.calibration_pack_btn.setToolTip(
        "下载并缓存一套公开的通用图片，作为无需项目数据的 INT8 校准集。"
    )
    page.calibration_pack_btn.clicked.connect(page.download_generic_calibration_pack)
    page.calibration_pack_progress = QProgressBar()
    page.calibration_pack_progress.setRange(0, 100)
    page.calibration_pack_progress.setValue(0)
    page.calibration_pack_progress.setFormat("下载通用校准集 %p%")
    page.calibration_pack_progress.setVisible(False)
    page.validate_quantized_box, page.validate_quantized_check = page.checkbox_with_help(
        "量化后验证",
        settings.validate_quantized,
        "使用 ONNX Runtime 执行前向冒烟验证，检查输入输出、形状和有限数值。",
    )
    page.validation_samples_box, page.validation_samples_spin = _spin_field(
        page,
        "验证样本数",
        settings.validation_samples,
        1,
        100000,
        "量化后冒烟验证的最大图片数量。",
    )
    for box in (
        page.calibration_data_box,
        page.calibration_samples_box,
        page.validation_samples_box,
    ):
        _configure_field_box(box)
    int8_layout.addWidget(page.calibration_data_box, 0, 0, 1, 2)
    int8_layout.addWidget(page.calibration_samples_box, 1, 0)
    int8_layout.addWidget(page.calibration_pack_btn, 1, 1)
    int8_layout.addWidget(page.calibration_pack_progress, 2, 0, 1, 2)
    int8_layout.addWidget(page.validate_quantized_box, 3, 0)
    int8_layout.addWidget(page.validation_samples_box, 3, 1)

    # Keep format-specific sections directly below the fixed fields in the two
    # baseline cards instead of introducing a third configuration card.
    source_layout = page.source_card.layout
    source_layout.addWidget(page.basic_options_box)
    source_layout.addStretch(1)
    source_layout.insertStretch(0, 1)
    source_layout.insertStretch(2, 1)
    source_layout.insertStretch(4, 1)
    page.inference_card.layout.addWidget(page.dynamic_box)
    page.inference_card.layout.addWidget(page.int8_box)
    page.inference_card.layout.addStretch(1)


def arrange_basic_option_row(page, export_argument: str) -> None:
    """Reorder the shared format options and keep every visible cell equal-width."""
    order = {
        "onnx": (
            page.basic_format_box,
            page.nms_box,
            page.agnostic_nms_check,
            page.dynamic_input_check,
        ),
        "torchscript": (
            page.basic_format_box,
            page.nms_box,
            page.agnostic_nms_check,
            page.dynamic_input_check,
        ),
        "openvino": (
            page.nms_box,
            page.agnostic_nms_check,
            page.dynamic_input_check,
            page.basic_format_box,
        ),
        "engine": (
            page.basic_format_box,
            page.nms_box,
            page.agnostic_nms_check,
            page.dynamic_input_check,
        ),
    }.get(export_argument)
    if order is None:
        order = (
            page.basic_format_box,
            page.nms_box,
            page.agnostic_nms_check,
            page.dynamic_input_check,
        )

    layout = page.basic_option_row.layout()
    stretch = layout.takeAt(layout.count() - 1)
    stretch_factors = (135, 100, 100, 100) if export_argument == "torchscript" else (1, 1, 1, 1)
    explicit_visibility = {
        widget: not widget.isHidden()
        for widget in order
    }
    while layout.count():
        item = layout.takeAt(0)
        if item.widget() is not None:
            item.widget().setParent(page.basic_option_row)
    for index, widget in enumerate(order):
        layout.addWidget(widget, stretch_factors[index])
        layout.setStretch(index, stretch_factors[index])
        widget.setVisible(explicit_visibility[widget])
    if stretch.spacerItem() is not None:
        layout.addItem(stretch)
    visible = [widget for widget in order if not widget.isHidden()]
    widths = []
    for widget in visible:
        if widget is page.basic_format_box:
            widths.append(
                max(
                    page.simplify_check.fontMetrics().horizontalAdvance(
                        page.simplify_check.text()
                    )
                    + 24,
                    page.optimize_check.fontMetrics().horizontalAdvance(
                        page.optimize_check.text()
                    )
                    + 24,
                )
            )
        else:
            check = widget.findChild(QCheckBox) or widget
            widths.append(
                max(
                    widget.sizeHint().width(),
                    check.fontMetrics().horizontalAdvance(check.text()) + 24,
                )
            )
    spacing = layout.spacing()
    page.basic_option_row.setMinimumWidth(
        sum(widths)
        + max(0, len(visible) - 1) * spacing
        + 48
    )


def _build_action_row(page, root_layout) -> None:
    page.install_btn = QPushButton("安装/替换附加包")
    page.install_btn.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
    page.install_btn.setFixedWidth(144)
    page.install_btn.setToolTip("选择并安装或替换模型格式转换附加环境包")
    page.install_btn.clicked.connect(page.choose_model_export_package)
    page.install_status = QLabel()
    page.install_status.setMinimumWidth(150)
    page.install_status.setVisible(False)
    page.install_btn.setVisible(installed_variant() != CPU_VARIANT)
    page.install_controls = QHBoxLayout()
    page.install_controls.setContentsMargins(0, 0, 0, 0)
    page.install_controls.setSpacing(8)

    page.preview_btn = QPushButton("预览转换")
    page.preview_btn.clicked.connect(page.preview_export)
    page.start_btn = QPushButton("开始转换")
    page.start_btn.clicked.connect(page.start_export)
    page.stop_btn = QPushButton("停止")
    page.stop_btn.setEnabled(False)
    page.stop_btn.clicked.connect(page.stop_export)
    page.open_btn = QPushButton("打开结果文件夹")
    page.open_btn.clicked.connect(page.open_output_dir)
    for button in (page.preview_btn, page.start_btn, page.stop_btn, page.open_btn):
        button.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        page.install_controls.addWidget(button)
    page.install_controls.addStretch(1)
    page.install_controls.addWidget(page.install_btn)
    page.install_controls.addWidget(page.install_status)
    root_layout.addLayout(page.install_controls)


def _top_row_layout(left: QWidget, right: QWidget) -> QHBoxLayout:
    layout = QHBoxLayout()
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(16)
    layout.addWidget(left, 3)
    layout.addWidget(right, 2)
    return layout


def update_model_export_card_ratio(page) -> None:
    """Keep the default 3:2 card ratio while protecting the option row."""
    top_box = getattr(page, "onnx_top_box", None)
    top_layout = getattr(page, "onnx_top_layout", None)
    if top_box is None or top_layout is None or top_box.width() <= 0:
        return

    ratio = 1.5
    if not page.basic_options_box.isHidden():
        margins = top_layout.contentsMargins()
        available = (
            top_box.width()
            - margins.left()
            - margins.right()
            - top_layout.spacing()
        )
        if available > 0:
            card_margins = page.source_card.layout.contentsMargins()
            required_left = max(
                page.basic_option_row.minimumSizeHint().width(),
                page.basic_option_row.minimumWidth(),
            ) + (
                card_margins.left() + card_margins.right()
            )
            default_left = available * 3 / 5
            if required_left > default_left:
                ratio = required_left / max(1, available - required_left)
                ratio = min(2.0, max(1.5, ratio))

    left_stretch = round(ratio * 100)
    right_stretch = 100
    top_layout.setStretch(0, left_stretch)
    top_layout.setStretch(1, right_stretch)
    top_layout.invalidate()
    page._model_export_card_ratio = left_stretch / right_stretch


def _spin_field(page, label: str, value: int, minimum: int, maximum: int, help_text: str):
    box = QWidget()
    layout = QVBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    caption_box, _caption, _icon = page._caption_widget(label, help_text=help_text)
    spin = QSpinBox()
    spin.setRange(minimum, maximum)
    spin.setValue(int(value))
    layout.addWidget(caption_box)
    layout.addWidget(spin)
    return box, spin


def _double_spin_field(
    page,
    label: str,
    value: float,
    minimum: float,
    maximum: float,
    step: float,
    help_text: str,
):
    box = QWidget()
    layout = QVBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    caption_box, _caption, _icon = page._caption_widget(label, help_text=help_text)
    spin = QDoubleSpinBox()
    spin.setRange(minimum, maximum)
    spin.setSingleStep(step)
    spin.setDecimals(2)
    spin.setValue(float(value))
    layout.addWidget(caption_box)
    layout.addWidget(spin)
    return box, spin


def _double_spin(value: float, label: str, help_text: str) -> QDoubleSpinBox:
    spin = QDoubleSpinBox()
    spin.setRange(0.0, 1.0)
    spin.setDecimals(3)
    spin.setSingleStep(0.05)
    spin.setValue(float(value))
    spin.setToolTip(help_text)
    spin.setObjectName(f"modelExport{label.replace(' ', '')}Spin")
    return spin


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


def _checkbox(page, label: str, checked: bool, help_text: str) -> QCheckBox:
    checkbox = QCheckBox(label)
    checkbox.setChecked(bool(checked))
    page._set_help_target(checkbox, label, help_text)
    return checkbox


def _precision_label(value: str) -> str:
    return {"fp16": "FP16", "int8": "INT8"}.get(str(value).lower(), "FP32")


__all__ = ["build_model_export_layout"]
