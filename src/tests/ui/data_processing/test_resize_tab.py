from pathlib import Path

import os
from unittest.mock import patch

import subprocess

import sys

from types import SimpleNamespace
from unittest.mock import Mock

from src.tests.helpers.ui_paths import (
    APP,
    DATA_VIEW,
    HOME_VIEW,
    ICON_ICO,
    ICON_PNG,
    INSTALLER_ISS,
    PACKAGING_DOC,
    PACKAGING_PACKAGE_SCRIPT,
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


def test_resize_page_switches_between_canvas_and_crop_controls(tmp_path):
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

    assert page.mode_combo.currentText() == "画布压缩"
    assert page.bg_box.isEnabled()
    page.mode_combo.setCurrentText("裁剪")
    page.ratio_combo.setCurrentText("4:3")
    page.size_edit.setText("640×480")

    assert settings.image_resize.mode == "裁剪"
    assert settings.image_resize.aspect_ratio == "4:3"
    assert settings.image_resize.resolution == "640×480"
    assert not page.bg_box.isEnabled()
    assert page.config().resolution == "640×480"


def test_dataset_split_tab_reads_annotation_managed_categories(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.data.convert.tab import ConvertTab

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    settings.dataset.class_names = ["weld", "scratch"]
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )

    page = ConvertTab(fake_app)

    assert page.config().class_names == ["weld", "scratch"]
    assert [page.task_combo.itemText(index) for index in range(page.task_combo.count())] == [
        "detect",
        "obb",
        "seg",
        "pose",
    ]
    assert [page.mode_combo.itemText(index) for index in range(page.mode_combo.count())] == [
        "Labelme 转 YOLO 并划分数据集",
        "YOLO 原生数据集划分",
    ]
    assert not hasattr(page, "line_edit")
    assert not hasattr(page, "seed_edit")
    assert page.config().random_seed == settings.dataset.random_seed
    assert not page.class_mapping_btn.isHidden()
    assert page.task_box.isEnabled()
    assert page.task_combo.isEnabled()

    page.mode_combo.setCurrentText("YOLO 原生数据集划分")
    config = page.config()
    assert config.source_format == "yolo"
    assert config.annotations_dir == Path(settings.paths.labels_dir)
    assert settings.conversion.use_labelme is False
    assert page.class_mapping_btn.isHidden()
    assert page.backup_yolo_check.isEnabled()
    assert not page.task_box.isEnabled()
    assert not page.task_combo.isEnabled()

    native_settings = build_default_settings(tmp_path / "native")
    native_settings.conversion.use_labelme = False
    native_page = ConvertTab(
        SimpleNamespace(
            settings=native_settings,
            settings_service=SimpleNamespace(save=lambda _data: None),
        )
    )
    assert native_page.mode_combo.currentText() == "YOLO 原生数据集划分"
    assert native_page.class_mapping_btn.isHidden()
    assert native_page.backup_yolo_check.isEnabled()
    assert not native_page.task_box.isEnabled()


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


def test_dataset_split_execution_dispatches_to_background_task(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.data.convert.tab import ConvertTab

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    calls = {}
    worker = SimpleNamespace(
        progress=Mock(),
        finished_with_payload=Mock(),
        finished=Mock(),
    )

    def run_background(kind, fn, *, receiver=None, accepts_progress=False):
        calls.update(
            kind=kind,
            fn=fn,
            receiver=receiver,
            accepts_progress=accepts_progress,
        )
        return worker

    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=run_background,
    )
    page = ConvertTab(fake_app)

    page.run_button.click()

    assert calls["kind"] == "conversion_run"
    assert calls["receiver"] is page
    assert calls["accepts_progress"] is True
    assert not page.preview_button.isEnabled()
    assert not page.run_button.isEnabled()
    assert page.run_button.text() == "执行划分 0%"
    worker.progress.connect.assert_called_once()
    worker.finished_with_payload.connect.assert_called_once()
    worker.finished.connect.assert_called_once()

    progress_callback = worker.progress.connect.call_args.args[0]
    progress_callback("写入数据集", 35)
    assert page.run_button.text() == "执行划分 35%"
    assert "写入数据集：35%" in page.log.toPlainText()

    finished_callback = worker.finished.connect.call_args.args[0]
    finished_callback()
    assert page.preview_button.isEnabled()
    assert page.run_button.isEnabled()
    assert page.run_button.text() == "执行划分"
