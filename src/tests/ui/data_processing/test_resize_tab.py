from pathlib import Path

import os
from unittest.mock import patch

import subprocess

import sys

from types import SimpleNamespace

from src.tests.helpers.ui_paths import (
    APP,
    DATA_VIEW,
    HOME_VIEW,
    ICON_ICO,
    ICON_PNG,
    INSTALLER_ISS,
    PACKAGING_DOC,
    PACKAGING_ONE_CLICK_SCRIPT,
    PACKAGING_SCRIPT,
    PACKAGING_SPEC,
    PAGE_BASE,
    SETTINGS_VIEW,
    TRAIN_VIEW,
    UI_BUNDLE_PATHS,
    VALIDATE_VIEW,
    WINDOW,
)


def _read_app():
    return APP.read_text(encoding="utf-8")

def _read_ui_bundle():
    return "\n".join(path.read_text(encoding="utf-8") for path in UI_BUNDLE_PATHS)


def test_resize_page_has_open_output_button_and_opens_output_dir(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.data.resize.tab import ResizeTab

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )

    page = ResizeTab(fake_app)
    output_dir = tmp_path / "resized-output"
    page.output_edit.setText(str(output_dir))

    with patch("src.ui.features.data.resize.tab.os.startfile") as startfile:
        page.open_output_btn.click()

    assert page.open_output_btn.text() == "打开结果文件夹"
    assert output_dir.exists()
    startfile.assert_called_once_with(output_dir)


def test_dataset_split_tab_reads_annotation_managed_categories(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.data.convert.tab import ConvertTab

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    settings["dataset"]["class_names"] = ["weld", "scratch"]
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )

    page = ConvertTab(fake_app)

    assert page.config().class_names == ["weld", "scratch"]


def test_class_mapping_rows_use_zero_based_left_indices(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.shared.qt import QApplication
    from src.ui.shared.dialogs import ClassMappingDialog

    app = QApplication.instance() or QApplication([])
    dialog = ClassMappingDialog(["weld", "scratch"])

    assert [
        dialog.table.verticalHeaderItem(index).text()
        for index in range(dialog.table.rowCount())
    ] == ["0", "1"]
