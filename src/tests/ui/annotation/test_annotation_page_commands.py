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

from src.tests.helpers.ui_source import read_app as _read_app, read_ui_bundle as _read_ui_bundle, show_page as _show_annotation_page

def test_annotation_settings_can_enable_optimized_mirror_edit():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.shared.qt import QApplication
    from src.ui.features.annotation.dialogs import AnnotationSettingsDialog

    app = QApplication.instance() or QApplication([])
    dialog = AnnotationSettingsDialog(
        False,
        10,
        True,
        False,
        False,
        False,
        False,
        "labels",
        load_yolo_when_labelme_missing=True,
        optimize_mirror_edit=True,
    )

    assert dialog.optimize_mirror_check.isChecked() is True
    assert dialog.load_yolo_missing_check.isChecked() is True
    assert dialog.values()[-1] is True

def test_annotation_settings_places_yolo_fallback_above_annotation_names():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.shared.qt import QApplication
    from src.ui.features.annotation.dialogs import AnnotationSettingsDialog

    app = QApplication.instance() or QApplication([])
    dialog = AnnotationSettingsDialog(
        False,
        10,
        True,
        False,
        False,
        False,
        False,
        "labels",
    )

    load_yolo_index = dialog.layout().indexOf(
        dialog.load_yolo_missing_check.parentWidget()
    )
    show_names_index = dialog.layout().indexOf(
        dialog.show_annotation_names_check.parentWidget()
    )

    assert load_yolo_index < show_names_index

def test_annotation_page_canvas_context_save_flags_follow_auto_save_settings(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AnnotationPage

    images_dir = tmp_path / "images"
    images_dir.mkdir()
    from PIL import Image

    Image.new("RGB", (32, 32), "white").save(images_dir / "1.jpg")

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    settings.annotation.auto_save = False
    settings.annotation.auto_convert_yolo = False
    settings.annotation.show_yolo_save_in_context_menu = True
    settings.task.mode = "detect"
    settings.task.mode_selected = True
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )

    page = _show_annotation_page(AnnotationPage(fake_app), app)
    assert page.canvas.can_save_default is False
    assert page.canvas.can_save_labelme is True
    assert page.canvas.can_save_yolo is True
    assert page.canvas.can_undo is False

    settings.annotation.auto_save = True
    page._refresh_manual_action_buttons()
    assert page.canvas.can_save_labelme is False
    assert page.canvas.can_save_yolo is True

    settings.annotation.auto_convert_yolo = True
    page._refresh_manual_action_buttons()
    assert page.canvas.can_save_labelme is False
    assert page.canvas.can_save_yolo is False

def test_annotation_page_context_delete_image_removes_image_and_labels(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    import json

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AnnotationPage

    images_dir = tmp_path / "images"
    images_dir.mkdir()
    from PIL import Image

    image_path = images_dir / "1.jpg"
    Image.new("RGB", (32, 32), "white").save(image_path)
    (images_dir / "1.json").write_text(
        json.dumps(
            {
                "imagePath": "1.jpg",
                "imageWidth": 32,
                "imageHeight": 32,
                "shapes": [{"label": "weld", "points": [[1, 1], [10, 10]], "shape_type": "rectangle"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    labels_dir = tmp_path / "labels"
    labels_dir.mkdir()
    (labels_dir / "1.txt").write_text("0 0.5 0.5 0.2 0.2\n", encoding="utf-8")

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    settings.paths.labels_dir = str(labels_dir)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )

    page = _show_annotation_page(AnnotationPage(fake_app), app)
    page.delete_image_and_annotations(image_path)

    assert image_path.exists() is False
    assert (images_dir / "1.json").exists() is False
    assert (labels_dir / "1.txt").exists() is False

def test_annotation_page_w_shortcut_opens_draw_shape_dialog(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication, QDialog, Qt
    from src.ui.features.annotation.page import AnnotationPage
    import src.ui.features.annotation.settings_actions as settings_actions

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )
    calls = []

    class FakeDrawShapeDialog:
        def __init__(self, line_expand_enabled, parent, **kwargs):
            calls.append((line_expand_enabled, parent, kwargs))

        def exec(self):
            return QDialog.DialogCode.Rejected

    monkeypatch.setattr(settings_actions, "DrawShapeDialog", FakeDrawShapeDialog)
    page = AnnotationPage(fake_app)

    page._draw_shortcut.activated.emit()

    assert page._draw_shortcut.key().toString() == "W"
    assert page._draw_shortcut.context() == Qt.ShortcutContext.WidgetWithChildrenShortcut
    assert calls == [
        (
            False,
            page,
            {
                "sam_models": page.sam_assist.models,
                "selected_sam_model": "sam2.1_hiera_base_plus.pt",
                "sam_enabled": False,
                    "sam_toggle_callback": page.sam_assist.set_enabled,
                    "sam_model_callback": page.sam_assist.select_model,
                    "sam_settings": page.sam_assist.parameters(),
                    "sam_settings_callback": page.sam_assist.apply_parameters,
                },
        )
    ]
