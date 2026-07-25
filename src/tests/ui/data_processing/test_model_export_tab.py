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
    best = tmp_path / "result" / "train-3" / "weights" / "best.pt"
    model.parent.mkdir(parents=True)
    best.parent.mkdir(parents=True)
    model.write_bytes(b"model")
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
    assert page.start_btn.text() == "开始转换"
    assert page.install_btn.text() == "安装/替换附加包"
    assert page.install_btn.width() == 150
    assert not page.install_progress.isVisible()
    assert page.app.settings["model_export"]["output_dir"].endswith(
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

    assert page.install_controls.stretch(0) == 1
    page.model_export_package_installing_changed(True)
    assert page.install_btn.isHidden()
    assert not page.install_progress.isHidden()
    assert page.install_controls.stretch(0) == 0

    page.model_export_package_installing_changed(False)
    assert not page.install_btn.isHidden()
    assert page.install_progress.isHidden()
    assert page.install_controls.stretch(0) == 1


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
    assert "未安装模型转换环境包" in page.environment_status.text()
    page._set_running_state(True)
    assert not page.start_btn.isEnabled()
    assert not page.install_btn.isEnabled()
    assert page.stop_btn.isEnabled()


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
