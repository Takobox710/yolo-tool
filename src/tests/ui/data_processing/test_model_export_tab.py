from __future__ import annotations

import os
from types import SimpleNamespace


def test_model_export_tab_scans_models_and_exposes_all_formats(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.data.model_export.tab import ModelExportTab

    app = QApplication.instance() or QApplication([])
    model = tmp_path / "data" / "models" / "base.pt"
    sam = tmp_path / "data" / "models" / "sam2.1_hiera_base_plus.pt"
    best = tmp_path / "result" / "train-3" / "weights" / "best.pt"
    model.parent.mkdir(parents=True)
    best.parent.mkdir(parents=True)
    model.write_bytes(b"model")
    sam.write_bytes(b"sam")
    best.write_bytes(b"best")
    fake_app = SimpleNamespace(
        settings=build_default_settings(tmp_path),
        settings_service=SimpleNamespace(save=lambda _data: None),
        workers=[],
        export_handle=None,
    )

    page = ModelExportTab(fake_app)

    model_choices = [
        page.model_combo.itemText(i) for i in range(page.model_combo.count())
    ]
    assert "data\\models\\base.pt" not in model_choices
    assert "data\\models\\sam2.1_hiera_base_plus.pt" not in model_choices
    assert "train-3\\best.pt" in model_choices
    assert page._model_display_path(best) == "train-3\\best.pt"
    assert page.model_path_from_text("train-3\\best.pt") == str(best.resolve())
    assert [page.format_combo.itemText(i) for i in range(page.format_combo.count())] == [
        "ONNX",
        "TorchScript",
        "OpenVINO",
        "TensorRT",
        "NCNN",
    ]
    assert "SAM2 ONNX" not in [
        page.format_combo.itemText(i) for i in range(page.format_combo.count())
    ]
    assert page.start_btn.text() == "开始转换"
    assert page.install_btn.text() == "安装/替换附加包"
    assert page.calibration_pack_btn.text() == "获取通用校准集"
    assert not page.calibration_pack_progress.isVisible()
    assert page.install_btn.width() == 144
    assert not page.install_progress.isVisible()
    assert page.context.settings.model_export.output_dir.endswith(
        "data\\models\\model_exports"
    )


def test_model_export_package_progress_replaces_right_aligned_button(tmp_path):
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

    assert [
        page.install_controls.indexOf(button)
        for button in (
            page.preview_btn,
            page.start_btn,
            page.stop_btn,
            page.open_btn,
            page.install_btn,
        )
    ] == [0, 1, 2, 3, 5]
    page.model_export_package_installing_changed(True)
    assert page.install_btn.isHidden()
    assert not page.install_progress.isHidden()
    assert page.install_controls.indexOf(page.install_progress) == 6

    page.model_export_package_installing_changed(False)
    assert not page.install_btn.isHidden()
    assert page.install_progress.isHidden()
    assert page.install_controls.indexOf(page.install_btn) == 5


def test_model_export_layout_balances_columns_and_groups_options(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication, QLabel, QCheckBox, QFrame
    from src.ui.features.data.model_export.tab import ModelExportTab

    app = QApplication.instance() or QApplication([])
    fake_app = SimpleNamespace(
        settings=build_default_settings(tmp_path),
        settings_service=SimpleNamespace(save=lambda _data: None),
        workers=[],
        export_handle=None,
    )
    page = ModelExportTab(fake_app)
    page.resize(1100, 740)
    page.show()
    app.processEvents()
    try:
        assert page._model_export_card_ratio == 1.5
        page.format_combo.setCurrentText("TorchScript")
        page.resize(800, 740)
        app.processEvents()
        assert page._model_export_card_ratio == 2.0
        page.resize(1000, 740)
        app.processEvents()
        assert 1.5 < page._model_export_card_ratio < 2.0
        assert page.basic_option_row.width() >= page.basic_option_row.minimumSizeHint().width()
        page.resize(1200, 740)
        app.processEvents()
        assert page._model_export_card_ratio == 1.5
        assert abs(page.model_box.width() - page.output_box.width()) <= 2
        assert abs(page.format_box.width() - page.precision_box.width()) <= 2
        assert page.model_combo.minimumWidth() == 0
        assert page.output_edit.minimumWidth() == 0
        assert page.onnx_top_box.isVisible()
        assert not hasattr(page, "config_scroll")
        assert page.layout().indexOf(page.install_controls) == 1
        assert len(page.findChildren(type(page.source_card), "card")) == 2
        assert page.source_card.layout.indexOf(page.onnx_source_grid) == 3
        assert abs(page.source_card.height() - page.onnx_right_card.height()) <= 1
        title = page.source_card.findChild(QLabel, "sectionTitle")
        assert title is not None and title.height() <= 30
        assert page.source_card.layout.count() == 7
        from PySide6.QtWidgets import QSpacerItem
        spacer_heights = [
            page.source_card.layout.itemAt(i).geometry().height()
            for i in range(page.source_card.layout.count())
            if isinstance(page.source_card.layout.itemAt(i), QSpacerItem)
        ]
        assert len(spacer_heights) == 4
        assert max(spacer_heights) - min(spacer_heights) <= 1
        assert page.onnx_source_grid.rowCount() == 2
        assert page.onnx_source_grid.verticalSpacing() == 10
        assert page.onnx_right_card.layout.count() == 5
        assert page.onnx_param_title.text() == "推理参数"
        assert page.onnx_param_title.objectName() == "sectionTitle"
        assert page.onnx_param_grid.indexOf(page.imgsz_box) >= 0
        assert page.onnx_param_grid.indexOf(page.batch_box) >= 0
        assert page.onnx_param_grid.getItemPosition(
            page.onnx_param_grid.indexOf(page.imgsz_box)
        )[:2] == (page.onnx_param_first_row, 0)
        assert page.onnx_param_grid.getItemPosition(
            page.onnx_param_grid.indexOf(page.batch_box)
        )[:2] == (page.onnx_param_first_row, 1)
        assert page.onnx_param_grid.indexOf(page.conf_box) >= 0
        assert page.onnx_param_grid.indexOf(page.iou_box) >= 0
        assert page.onnx_param_grid.indexOf(page.max_det_box) >= 0
        assert page.onnx_param_grid.getItemPosition(
            page.onnx_param_grid.indexOf(page.inference_format_box)
        )[:2] == (page.onnx_param_third_row, 1)
        assert page.onnx_simplify_btn.text().startswith("简化 ONNX")
        assert abs(page.imgsz_edit.height() - page.batch_spin.height()) <= 1
        assert page.imgsz_edit.objectName() == "modelExportFlatEdit"
        assert page.imgsz_edit.text() == "640"
        assert page.onnx_dynamic_row.indexOf(page.onnx_dynamic_batch_check) >= 0
        assert page.onnx_dynamic_row.indexOf(page.onnx_dynamic_size_check) >= 0
        assert page.onnx_dynamic_batch_check.isCheckable()
        assert page.onnx_dynamic_size_check.isCheckable()
        assert isinstance(page.onnx_simplify_btn, QCheckBox)
        assert isinstance(page.onnx_nms_btn, QCheckBox)
        assert isinstance(page.onnx_agnostic_btn, QCheckBox)
        assert page.onnx_simplify_btn.parentWidget() is page.simplify_box
        assert not hasattr(page, "format_option_card")
        assert not hasattr(page, "format_option_title")
        section_titles = {
            label.text()
            for label in page.findChildren(QLabel)
            if label.objectName() == "modelExportSectionTitle"
        }
        assert section_titles == {"INT8 校准与验证"}
        assert not page.basic_options_box.findChildren(QLabel, "modelExportSectionTitle")
        assert not page.basic_options_box.findChildren(QFrame, "modelExportSectionDivider")
        assert not page.dynamic_box.findChildren(QLabel, "modelExportSectionTitle")
        assert not page.dynamic_box.findChildren(QFrame, "modelExportSectionDivider")
        assert not page.nms_box.findChildren(QLabel, "modelExportSectionTitle")
        assert not page.nms_box.findChildren(QFrame, "modelExportSectionDivider")
        assert page.basic_options_grid.getItemPosition(
            page.basic_options_grid.indexOf(page.basic_option_row)
        )[:2] == (0, 0)
        assert page.basic_option_row.layout().indexOf(page.basic_format_box) >= 0
        assert page.basic_option_row.layout().indexOf(page.nms_box) >= 0
        assert page.basic_option_row.layout().indexOf(page.agnostic_nms_check) >= 0
        assert page.basic_option_row.layout().indexOf(page.dynamic_input_check) >= 0
        assert page.nms_layout.indexOf(page.nms_check) >= 0
        assert page.nms_layout.indexOf(page.agnostic_nms_check) == -1
        fixed_positions = {
            name: page.onnx_param_grid.getItemPosition(page.onnx_param_grid.indexOf(widget))[:2]
            for name, widget in (
                ("imgsz", page.imgsz_box),
                ("batch", page.batch_box),
                ("conf", page.conf_box),
                ("iou", page.iou_box),
                ("max_det", page.max_det_box),
            )
        }
        for format_name in ("TorchScript", "OpenVINO", "TensorRT", "NCNN"):
            page.format_combo.setCurrentText(format_name)
            assert page.onnx_source_grid.indexOf(page.model_box) >= 0
            assert page.onnx_param_grid.indexOf(page.imgsz_box) >= 0
            assert {
                name: page.onnx_param_grid.getItemPosition(
                    page.onnx_param_grid.indexOf(widget)
                )[:2]
                for name, widget in (
                    ("imgsz", page.imgsz_box),
                    ("batch", page.batch_box),
                    ("conf", page.conf_box),
                    ("iou", page.iou_box),
                    ("max_det", page.max_det_box),
                )
            } == fixed_positions
            assert page.source_card.layout.indexOf(page.basic_options_box) >= 0
            assert page.basic_option_row.layout().indexOf(page.nms_box) >= 0
            assert page.inference_card.layout.indexOf(page.dynamic_box) >= 0
            assert page.inference_grid.indexOf(page.dynamic_box) == -1
            if format_name in ("TorchScript", "OpenVINO", "TensorRT"):
                assert not page.dynamic_input_check.isHidden()
                assert page.basic_option_row.layout().indexOf(
                    page.dynamic_input_check
                ) >= 0
                assert not page.nms_check.isHidden()
                assert page.nms_box.width() >= page.nms_check.sizeHint().width()
                if format_name == "TorchScript":
                    assert page.optimize_check.sizeHint().width() <= page.optimize_box.width()
            else:
                assert page.dynamic_input_check.isHidden()
            assert page.inference_card.layout.indexOf(page.int8_box) >= 0
    finally:
        page.close()


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


def test_data_page_registers_model_export_secondary_page(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.data.page import DataPage

    app = QApplication.instance() or QApplication([])
    fake_app = SimpleNamespace(
        settings=build_default_settings(tmp_path),
        settings_service=SimpleNamespace(save=lambda _data: None),
        workers=[],
        export_handle=None,
    )

    page = DataPage(fake_app)

    assert "model_export" in page.tools
    assert list(page.tools) == ["convert", "preview", "rename", "resize", "model_export"]
    assert page.tool_buttons["model_export"].text() == "🗂️ 模型格式转换"
    page.show_tool("model_export")
    assert page.tool_stack.currentWidget() is page.tools["model_export"]


def test_model_export_environment_status_and_running_state(monkeypatch, tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.model_export import ExportCapability
    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.data.model_export import tab as tab_module

    app = QApplication.instance() or QApplication([])
    fake_app = SimpleNamespace(
        settings=build_default_settings(tmp_path),
        settings_service=SimpleNamespace(save=lambda _data: None),
        workers=[],
        export_handle=None,
    )
    monkeypatch.setattr(
        tab_module,
        "export_capability",
        lambda _format: ExportCapability(
            False, "独立转换环境", "未安装模型转换环境包。"
        ),
    )
    page = tab_module.ModelExportTab(fake_app)

    page.format_combo.setCurrentText("OpenVINO")
    assert not hasattr(page, "environment_status")
    page._set_running_state(True)
    assert not page.start_btn.isEnabled()
    assert not page.install_btn.isEnabled()
    assert page.stop_btn.isEnabled()


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


def test_model_export_drop_recognizes_archive_and_requests_confirmation(
    monkeypatch, tmp_path
):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication, QMessageBox
    from src.ui.features.data.model_export.tab import ModelExportTab
    from src.ui.shared import model_export_package as drop_module

    app = QApplication.instance() or QApplication([])
    fake_app = SimpleNamespace(
        settings=build_default_settings(tmp_path),
        settings_service=SimpleNamespace(save=lambda _data: None),
        workers=[],
        export_handle=None,
    )
    page = ModelExportTab(fake_app)
    package = tmp_path / "runtime.7z"
    package.write_bytes(b"archive")
    selected = []
    monkeypatch.setattr(
        drop_module,
        "inspect_extension_package_fast",
        lambda _path: {
            "version": "runtime-1",
            "supported_formats": ["engine"],
        },
    )
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *_args, **_kwargs: QMessageBox.StandardButton.Yes,
    )
    monkeypatch.setattr(
        page,
        "install_model_export_package",
        lambda path: selected.append(path),
    )

    page.confirm_model_export_package(package)

    assert page.acceptDrops()
    assert selected == [package]
