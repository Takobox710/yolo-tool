from __future__ import annotations

import os
from types import SimpleNamespace

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
