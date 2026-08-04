from __future__ import annotations

import os
from types import SimpleNamespace

def test_model_export_options_follow_format_model_and_precision(monkeypatch, tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.data.model_export.tab import ModelExportTab

    app = QApplication.instance() or QApplication([])
    yolo = tmp_path / "result" / "train-1" / "weights" / "best.pt"
    sam = tmp_path / "data" / "models" / "sam2.1_hiera_base_plus.pt"
    yolo.parent.mkdir(parents=True)
    sam.parent.mkdir(parents=True)
    yolo.write_bytes(b"yolo")
    sam.write_bytes(b"sam")
    fake_app = SimpleNamespace(
        settings=build_default_settings(tmp_path),
        settings_service=SimpleNamespace(save=lambda _data: None),
        workers=[],
        export_handle=None,
    )

    monkeypatch.setattr(
        "src.ui.features.data.model_export.tab.export_capability",
        lambda _format, **_kwargs: SimpleNamespace(
            available=True, runtime="test", reason="ok", executable=None
        ),
    )
    page = ModelExportTab(fake_app)
    page.format_combo.setCurrentText("ONNX")
    assert not page.imgsz_box.isHidden()
    assert not page.dynamic_box.isHidden()
    assert not page.nms_box.isHidden()
    assert page.int8_box.isHidden()
    assert not page.inference_format_box.isHidden()
    assert not page.opset_box.isHidden()
    assert page.workspace_box.isHidden()

    assert [page.precision_combo.itemText(i) for i in range(page.precision_combo.count())] == [
        "FP32",
        "FP16",
        "INT8",
    ]
    page.precision_combo.setCurrentText("INT8")
    assert not page.int8_box.isHidden()
    assert not page.validate_quantized_box.isHidden()

    page.format_combo.setCurrentText("TorchScript")
    assert page.onnx_param_grid.indexOf(page.imgsz_box) >= 0
    assert page.onnx_param_grid.indexOf(page.batch_box) >= 0
    assert not hasattr(page, "format_option_card")
    assert page.simplify_box.isHidden()
    assert page.dynamic_box.isHidden()
    assert not page.dynamic_input_check.isHidden()
    assert page.dynamic_batch_check.isHidden()
    assert page.dynamic_height_check.isHidden()
    assert page.dynamic_width_check.isHidden()
    assert not page.nms_box.isHidden()
    assert not page.optimize_box.isHidden()
    assert page.basic_option_row.layout().indexOf(page.dynamic_input_check) >= 0
    assert not page.basic_format_box.isHidden()
    assert page.basic_option_row.layout().indexOf(page.basic_format_box) >= 0
    assert page.basic_option_row.layout().indexOf(page.nms_box) >= 0
    assert page.basic_option_row.layout().indexOf(page.agnostic_nms_check) >= 0
    assert page.int8_box.isHidden()
    assert page.inference_card.layout.indexOf(page.dynamic_box) >= 0

    page.format_combo.setCurrentText("OpenVINO")
    assert not hasattr(page, "format_option_card")
    assert page.dynamic_box.isHidden()
    assert not page.nms_box.isHidden()
    assert not page.dynamic_input_check.isHidden()
    page.resize(1400, 900)
    page.show()
    app.processEvents()
    assert page.basic_format_box.isHidden()
    assert page.nms_box.x() == 0
    assert page.agnostic_nms_check.x() == page.nms_box.width() + 12
    assert page.basic_option_row.layout().indexOf(page.dynamic_input_check) >= 0
    assert page.int8_box.isHidden()

    page.format_combo.setCurrentText("TensorRT")
    assert not hasattr(page, "format_option_card")
    assert not page.basic_options_box.isHidden()
    assert page.dynamic_box.isHidden()
    assert not page.nms_box.isHidden()
    assert not page.dynamic_input_check.isHidden()
    assert page.basic_option_row.layout().indexOf(page.dynamic_input_check) >= 0
    assert not page.simplify_box.isHidden()
    assert not page.basic_format_box.isHidden()
    assert not page.nms_check.isHidden()
    assert not page.agnostic_nms_check.isHidden()
    assert page.basic_option_row.layout().indexOf(page.basic_format_box) >= 0
    assert page.basic_option_row.layout().indexOf(page.nms_box) >= 0
    assert page.basic_option_row.layout().indexOf(page.agnostic_nms_check) >= 0
    assert page.basic_option_row.layout().indexOf(page.dynamic_input_check) >= 0
    assert not page.inference_format_box.isHidden()
    assert page.opset_box.isHidden()
    assert not page.workspace_box.isHidden()

    page.format_combo.setCurrentText("NCNN")
    assert page.simplify_box.isHidden()
    assert page.dynamic_box.isHidden()
    assert page.dynamic_input_check.isHidden()
    assert page.nms_box.isHidden()
    assert page.int8_box.isHidden()
    assert not hasattr(page, "format_option_card")
    assert not page.imgsz_box.isHidden()
    assert not page.batch_box.isHidden()
    assert not page.conf_spin.isEnabled()
    assert not page.iou_spin.isEnabled()
    assert not page.max_det_spin.isEnabled()

    sam_display = page._model_display_path(sam)
    page.model_combo.setCurrentText(sam_display)
    assert page.format_combo.currentText() == "ONNX"
    assert not page.imgsz_box.isHidden()
    assert not page.batch_box.isHidden()
    assert not page.imgsz_edit.isEnabled()
    assert not page.batch_spin.isEnabled()
    assert page.imgsz_edit.text() == "1024"
    assert page.batch_spin.value() == 1
    assert page.dynamic_box.isHidden()
    assert page.nms_box.isHidden()
    assert page.opset_box.isHidden()
    assert [page.precision_combo.itemText(i) for i in range(page.precision_combo.count())] == [
        "FP32",
        "FP16",
    ]
    assert page.precision_combo.currentText() == "FP32"
    assert page.int8_box.isHidden()
