from __future__ import annotations

from src.shared.qt import QCheckBox


def arrange_basic_option_row(page, export_argument: str) -> None:
    order = {"onnx": (page.basic_format_box, page.nms_box, page.agnostic_nms_check, page.dynamic_input_check), "torchscript": (page.basic_format_box, page.nms_box, page.agnostic_nms_check, page.dynamic_input_check), "openvino": (page.nms_box, page.agnostic_nms_check, page.dynamic_input_check, page.basic_format_box), "engine": (page.basic_format_box, page.nms_box, page.agnostic_nms_check, page.dynamic_input_check)}.get(export_argument)
    order = order or (page.basic_format_box, page.nms_box, page.agnostic_nms_check, page.dynamic_input_check)
    layout = page.basic_option_row.layout()
    stretch = layout.takeAt(layout.count() - 1)
    stretch_factors = (135, 100, 100, 100) if export_argument == "torchscript" else (1, 1, 1, 1)
    explicit_visibility = {widget: not widget.isHidden() for widget in order}
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
            widths.append(max(page.simplify_check.fontMetrics().horizontalAdvance(page.simplify_check.text()) + 24, page.optimize_check.fontMetrics().horizontalAdvance(page.optimize_check.text()) + 24))
        else:
            check = widget.findChild(QCheckBox) or widget
            widths.append(max(widget.sizeHint().width(), check.fontMetrics().horizontalAdvance(check.text()) + 24))
    page.basic_option_row.setMinimumWidth(sum(widths) + max(0, len(visible) - 1) * layout.spacing() + 48)


def update_model_export_card_ratio(page) -> None:
    top_box = getattr(page, "onnx_top_box", None)
    top_layout = getattr(page, "onnx_top_layout", None)
    if top_box is None or top_layout is None or top_box.width() <= 0:
        return
    ratio = 1.5
    if not page.basic_options_box.isHidden():
        margins = top_layout.contentsMargins()
        available = top_box.width() - margins.left() - margins.right() - top_layout.spacing()
        if available > 0:
            card_margins = page.source_card.layout.contentsMargins()
            required_left = max(page.basic_option_row.minimumSizeHint().width(), page.basic_option_row.minimumWidth()) + card_margins.left() + card_margins.right()
            default_left = available * 3 / 5
            if required_left > default_left:
                ratio = min(2.0, max(1.5, required_left / max(1, available - required_left)))
    left_stretch = round(ratio * 100)
    top_layout.setStretch(0, left_stretch)
    top_layout.setStretch(1, 100)
    top_layout.invalidate()
    page._model_export_card_ratio = left_stretch / 100


__all__ = ["arrange_basic_option_row", "update_model_export_card_ratio"]
