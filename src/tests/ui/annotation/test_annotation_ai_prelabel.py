from pathlib import Path

import os

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


def _show_annotation_page(page, app):
    page.on_show()
    app.processEvents()
    app.processEvents()
    return page


def test_ai_prelabel_dialog_ignores_stale_model_label_results_after_switch(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AiPrelabelDialog, AnnotationPage

    images_dir = tmp_path / "images"
    images_dir.mkdir()
    from PIL import Image

    Image.new("RGB", (32, 32), "white").save(images_dir / "1.jpg")
    first_model = tmp_path / "data" / "models" / "first.pt"
    second_model = tmp_path / "data" / "models" / "second.pt"
    first_model.parent.mkdir(parents=True)
    first_model.write_text("first", encoding="utf-8")
    second_model.write_text("second", encoding="utf-8")

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )

    page = _show_annotation_page(AnnotationPage(fake_app), app)
    dialog = AiPrelabelDialog(page)
    dialog._model_display_paths = {
        str(first_model): first_model,
        str(second_model): second_model,
    }
    dialog.model_combo.clear()
    dialog.model_combo.addItems([str(first_model), str(second_model)])
    dialog.model_combo.setCurrentText(str(first_model))

    dialog.model_combo.setCurrentText(str(second_model))
    dialog.apply_model_labels(str(first_model), ["stale-label"])

    assert dialog.model_labels == []
    dialog.apply_model_labels(str(second_model), ["fresh-label"])
    assert dialog.model_labels == ["fresh-label"]



def test_ai_prelabel_dialog_switches_to_sam3_text_prompts(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PIL import Image
    from src.services.settings import build_default_settings
    from src.shared.qt import QAbstractSpinBox, QApplication
    from src.ui.features.annotation.page import AiPrelabelDialog, AnnotationPage

    images_dir = tmp_path / "images"
    images_dir.mkdir()
    Image.new("RGB", (32, 32), "white").save(images_dir / "1.jpg")
    model_path = tmp_path / "data" / "models" / "sam3.pt"
    model_path.parent.mkdir(parents=True)
    model_path.write_bytes(b"sam3" * 512)

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    settings.dataset.class_names = ["weld", "scratch"]
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )

    page = _show_annotation_page(AnnotationPage(fake_app), app)
    dialog = AiPrelabelDialog(page)
    dialog.refresh_model_choices(str(model_path))
    assert dialog.model_combo.currentText() == "sam3.pt"
    assert dialog.model_combo.findText(str(model_path)) == -1
    assert dialog.resolved_model_path() == str(model_path.resolve())
    dialog.reload_model_labels()

    assert dialog.active_backend == "sam3"
    assert dialog.sam3_class_names == ["weld", "scratch"]
    assert [dialog.mapping_table.horizontalHeaderItem(i).text() for i in range(4)] == [
        "启用",
        "标注类别",
        "文本提示词",
        "状态",
    ]
    assert [edit.text() for edit in dialog.sam3_prompt_edits] == ["weld", "scratch"]
    assert "padding: 5px" in dialog.mapping_table.styleSheet()
    assert dialog.mapping_table.rowHeight(0) == 38
    assert all(
        "padding: 0" in edit.styleSheet() and edit.height() >= 28
        for edit in dialog.sam3_prompt_edits
    )
    assert all(check.isChecked() for check in dialog.sam3_checks)
    dialog.show()
    app.processEvents()
    assert dialog.threshold_widget.isHidden() is True
    assert dialog.sam3_advanced_toggle.isHidden() is False
    assert dialog.sam3_advanced_toggle.geometry().top() == dialog.shape_combo.geometry().top()
    assert "padding: 0" in dialog.model_combo.lineEdit().styleSheet()
    assert (
        dialog.sam3_simplify_spin.buttonSymbols()
        == QAbstractSpinBox.ButtonSymbols.NoButtons
    )
    dialog._set_backend_controls("yolo")
    assert dialog.threshold_widget.isVisible() is True
    dialog.close()



def test_ai_prelabel_dialog_keeps_scope_controls_compact(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication, QLabel
    from src.ui.features.annotation.page import AiPrelabelDialog, AnnotationPage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )

    page = AnnotationPage(fake_app)
    dialog = AiPrelabelDialog(page)
    dialog.reload_model_labels = lambda: None
    dialog.resize(700, 620)
    dialog.show()
    app.processEvents()

    options_title = next(
        label for label in dialog.findChildren(QLabel) if label.text() == "范围与模式"
    )
    assert dialog.range_combo.geometry().top() - options_title.geometry().bottom() <= 16
    assert dialog.append_radio.geometry().top() - dialog.range_combo.geometry().bottom() <= 16
    dialog.close()



def test_ai_prelabel_releases_canvas_sam_before_starting_worker(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PIL import Image
    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AiPrelabelDialog, AnnotationPage

    images_dir = tmp_path / "images"
    images_dir.mkdir()
    image_path = images_dir / "1.jpg"
    Image.new("RGB", (32, 32), "white").save(image_path)
    model_path = tmp_path / "data" / "models" / "model.pt"
    model_path.parent.mkdir(parents=True)
    model_path.write_bytes(b"model")

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    settings.dataset.class_names = ["weld"]
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )
    page = _show_annotation_page(AnnotationPage(fake_app), app)
    dialog = AiPrelabelDialog(page)
    events = []
    dialog.resolved_model_path = lambda: str(model_path)
    dialog.resolved_target_images = lambda: [image_path]
    dialog.current_range_mode = lambda: "当前图片"
    dialog.collect_mapping = lambda: {"0": "weld"}
    dialog._snapshot_targets = lambda _targets: None
    dialog._ensure_runtime_worker_started = lambda: None
    dialog.runtime_worker.start_ai_labeling = lambda _kwargs: events.append("worker")
    page.sam_assist.release_for_ai_prelabel = lambda: events.append("release")

    dialog.start_ai_labeling()

    assert events == ["release", "worker"]
    page.context.tasks.finish(dialog._ai_lease)
    dialog._ai_lease = None
    dialog.close()



