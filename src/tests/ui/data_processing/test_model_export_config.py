from __future__ import annotations

import os
from types import SimpleNamespace

def test_model_export_onnx_buttons_mirror_legacy_settings_and_dynamic_axes(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.data.model_export.tab import ModelExportTab

    app = QApplication.instance() or QApplication([])
    fake_app = SimpleNamespace(
        settings=build_default_settings(tmp_path),
        settings_service=SimpleNamespace(save=lambda _data: None),
        workers=[],
        export_handle=None,
    )
    page = ModelExportTab(fake_app)
    try:
        page.onnx_nms_btn.setChecked(True)
        page.onnx_agnostic_btn.setChecked(True)
        page.onnx_dynamic_batch_check.setChecked(True)
        page.onnx_dynamic_size_check.setChecked(True)
        page.onnx_conf_spin.setValue(0.35)
        page.onnx_iou_spin.setValue(0.55)
        page.onnx_max_det_spin.setValue(500)
        page.onnx_opset_spin.setValue(17)

        settings = page.context.settings.model_export
        assert settings.nms is True
        assert settings.agnostic_nms is True
        assert settings.dynamic_batch is True
        assert settings.dynamic_height is True
        assert settings.dynamic_width is True
        assert settings.nms_conf == 0.35
        assert settings.nms_iou == 0.55
        assert settings.nms_max_det == 500
        assert settings.opset == 17
    finally:
        page.close()

def test_model_export_collect_config_uses_onnx_layout_controls(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.data.model_export.tab import ModelExportTab

    app = QApplication.instance() or QApplication([])
    model = tmp_path / "result" / "train-1" / "weights" / "best.pt"
    model.parent.mkdir(parents=True)
    model.write_bytes(b"model")
    fake_app = SimpleNamespace(
        settings=build_default_settings(tmp_path),
        settings_service=SimpleNamespace(save=lambda _data: None),
        workers=[],
        export_handle=None,
    )
    page = ModelExportTab(fake_app)
    try:
        page.model_combo.setCurrentText("train-1\\best.pt")
        page.onnx_simplify_btn.setChecked(False)
        page.onnx_nms_btn.setChecked(True)
        page.onnx_agnostic_btn.setChecked(True)
        page.onnx_dynamic_batch_check.setChecked(True)
        page.onnx_dynamic_size_check.setChecked(True)
        page.batch_spin.setValue(2)
        page.onnx_conf_spin.setValue(0.31)
        page.onnx_iou_spin.setValue(0.61)
        page.onnx_max_det_spin.setValue(640)
        page.onnx_opset_spin.setValue(18)

        config = page.collect_config()

        assert config.simplify is False
        assert config.nms is True
        assert config.agnostic_nms is True
        assert config.dynamic_batch is True
        assert config.dynamic_height is True
        assert config.dynamic_width is True
        assert config.nms_conf == 0.31
        assert config.nms_iou == 0.61
        assert config.nms_max_det == 640
        assert config.opset == 18
    finally:
        page.close()

def test_model_export_non_onnx_uses_fixed_controls_and_preserves_format_options(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.data.model_export.tab import ModelExportTab

    app = QApplication.instance() or QApplication([])
    model = tmp_path / "result" / "train-1" / "weights" / "best.pt"
    model.parent.mkdir(parents=True)
    model.write_bytes(b"model")
    fake_app = SimpleNamespace(
        settings=build_default_settings(tmp_path),
        settings_service=SimpleNamespace(save=lambda _data: None),
        workers=[],
        export_handle=None,
    )
    page = ModelExportTab(fake_app)
    try:
        page.model_combo.setCurrentText("train-1\\best.pt")
        page.format_combo.setCurrentText("ONNX")
        page.onnx_simplify_btn.setChecked(False)
        page.onnx_nms_btn.setChecked(True)
        page.onnx_dynamic_batch_check.setChecked(True)
        page.onnx_dynamic_size_check.setChecked(True)
        page.onnx_opset_spin.setValue(17)
        page.conf_spin.setValue(0.31)

        page.format_combo.setCurrentText("TensorRT")
        page.dynamic_input_check.setChecked(True)
        page.workspace_spin.setValue(8.0)
        page.nms_check.setChecked(True)
        page.batch_spin.setValue(2)
        config = page.collect_config()

        assert config.export_format == "engine"
        assert config.imgsz == 640
        assert config.batch == 2
        assert config.dynamic_batch is True
        assert config.dynamic_height is True
        assert config.dynamic_width is True
        assert config.nms is True
        assert config.nms_conf == 0.31
        assert config.workspace == 8.0
        assert config.opset is None

        page.format_combo.setCurrentText("ONNX")
        assert page.onnx_simplify_btn.isChecked() is False
        assert page.onnx_dynamic_batch_check.isChecked() is True
        assert page.onnx_dynamic_size_check.isChecked() is True
        assert page.onnx_opset_spin.value() == 17

        page.format_combo.setCurrentText("TensorRT")
        assert page.dynamic_input_check.isChecked() is True
        assert page.workspace_spin.value() == 8.0
        assert page.nms_check.isChecked() is True

        page.format_combo.setCurrentText("NCNN")
        assert not hasattr(page, "format_option_card")
        assert not page.imgsz_box.isHidden()
        assert not page.batch_box.isHidden()
        assert not page.conf_spin.isEnabled()
    finally:
        page.close()
