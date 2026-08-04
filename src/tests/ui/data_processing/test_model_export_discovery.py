from __future__ import annotations

def test_model_export_tab_scans_models_and_exposes_all_formats(tmp_path, fake_app, qt_app):

    from src.ui.features.data.model_export.tab import ModelExportTab

    model = tmp_path / "data" / "models" / "base.pt"
    sam = tmp_path / "data" / "models" / "sam2.1_hiera_base_plus.pt"
    best = tmp_path / "result" / "train-3" / "weights" / "best.pt"
    model.parent.mkdir(parents=True)
    best.parent.mkdir(parents=True)
    model.write_bytes(b"model")
    sam.write_bytes(b"sam")
    best.write_bytes(b"best")

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
    assert page.context.settings.model_export.output_dir.endswith(
        "data\\models\\model_exports"
    )

def test_cpu_model_export_hides_extra_package_and_tensorrt(monkeypatch, fake_app, qt_app):

    from src.ui.features.data.model_export import layout, state
    from src.ui.features.data.model_export.tab import ModelExportTab

    monkeypatch.setattr(layout, "installed_variant", lambda: "cpu")
    monkeypatch.setattr(state, "installed_variant", lambda: "cpu")
    page = ModelExportTab(fake_app)
    try:
        formats = [page.format_combo.itemText(i) for i in range(page.format_combo.count())]
        assert formats == ["ONNX", "TorchScript", "OpenVINO", "NCNN"]
        assert not page.install_btn.isVisible()
        page.model_export_package_installing_changed(True)
        assert not page.install_btn.isVisible()
    finally:
        page.close()

def test_model_export_environment_status_and_running_state(monkeypatch, fake_app, qt_app):

    from src.services.model_export import ExportCapability
    from src.ui.features.data.model_export import tab as tab_module

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
