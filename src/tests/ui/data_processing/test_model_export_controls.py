from __future__ import annotations

import os
from types import SimpleNamespace

def test_model_export_package_install_keeps_button_without_progress_bar(tmp_path):
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

    assert page.install_controls.indexOf(page.install_btn) == 5
    assert not hasattr(page, "install_progress")
    assert page.install_status.isHidden()
    page.model_export_package_installing_changed(True)
    assert not page.install_btn.isHidden()
    assert not page.install_btn.isEnabled()
    assert page.install_status.text() == "正在准备安装"
    page.model_export_package_install_progress("解压附加环境", 5)
    assert page.install_status.text() == "解压附加环境 5%"

    page.model_export_package_installing_changed(False)
    assert not page.install_btn.isHidden()
    assert page.install_btn.isEnabled()
    assert page.install_status.text() == ""
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
        assert 1.5 <= page._model_export_card_ratio <= 2.0
        page.resize(1000, 740)
        app.processEvents()
        assert 1.5 <= page._model_export_card_ratio <= 2.0
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
        def visible_option_widths():
            return [
                widget.width()
                for widget in (
                    page.basic_format_box,
                    page.nms_box,
                    page.agnostic_nms_check,
                    page.dynamic_input_check,
                )
                if not widget.isHidden()
            ]

        assert page.basic_option_row.layout().indexOf(page.basic_format_box) == 0
        assert page.basic_format_box.width() >= page.nms_box.width()
        assert page.simplify_check.width() > 0
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
            app.processEvents()
            widths = visible_option_widths()
            if format_name == "TorchScript":
                assert page.basic_option_row.layout().indexOf(page.basic_format_box) == 0
                assert widths[0] >= max(widths[1:])
            elif format_name == "TensorRT":
                assert page.basic_option_row.layout().indexOf(page.basic_format_box) == 0
                assert max(widths) - min(widths) <= 2
            elif format_name != "NCNN":
                assert max(widths) - min(widths) <= 2
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
                    assert not page.optimize_box.isHidden()
                    assert page.simplify_box.isHidden()
                elif format_name == "TensorRT":
                    assert not page.simplify_box.isHidden()
                    assert page.optimize_box.isHidden()
                    assert page.simplify_check.width() > 0
                else:
                    assert page.simplify_box.isHidden()
                    assert page.optimize_box.isHidden()
            else:
                assert page.dynamic_input_check.isHidden()
            assert page.inference_card.layout.indexOf(page.int8_box) >= 0
    finally:
        page.close()
