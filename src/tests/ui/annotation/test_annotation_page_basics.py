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

def test_annotation_page_starts_without_a_default_class(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AnnotationPage

    app = QApplication.instance() or QApplication([])
    fake_app = SimpleNamespace(
        settings=build_default_settings(tmp_path),
        settings_service=SimpleNamespace(save=lambda _data: None),
    )

    page = AnnotationPage(fake_app)

    assert page.class_names() == []
    assert page.class_combo.count() == 0

def test_selected_annotation_syncs_target_type_and_combo_edits_annotation(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.annotation import EditableAnnotation
    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AnnotationPage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    settings.dataset.class_names = ["weld", "scratch"]
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )
    page = AnnotationPage(fake_app)
    page.canvas.annotations = [
        EditableAnnotation(
            1,
            "rect",
            [(1.0, 1.0), (10.0, 1.0), (10.0, 10.0), (1.0, 10.0)],
        )
    ]
    page.refresh_annotation_list()

    page.select_annotation(0)

    assert page.class_combo.currentIndex() == 1
    assert page.current_class_id == 1
    page.class_combo.setCurrentIndex(0)

    assert page.canvas.annotations[0].class_id == 0
    assert page.annotation_list.item(0).text().startswith("1.weld-")
    assert page.dirty is True

def test_annotation_sidebar_and_class_manager_buttons_are_chinese(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication, QDialogButtonBox, QLabel
    from src.ui.features.annotation.dialogs import ClassManagerDialog
    from src.ui.features.annotation.page import AnnotationPage

    app = QApplication.instance() or QApplication([])
    fake_app = SimpleNamespace(
        settings=build_default_settings(tmp_path),
        settings_service=SimpleNamespace(save=lambda _data: None),
    )
    page = AnnotationPage(fake_app)
    dialog = ClassManagerDialog(["weld"], page)

    assert any(label.text() == "目标类型：" for label in page.findChildren(QLabel))
    buttons = dialog.findChild(QDialogButtonBox)
    assert buttons is not None
    assert buttons.button(QDialogButtonBox.StandardButton.Ok).text() == "确定"
    assert buttons.button(QDialogButtonBox.StandardButton.Cancel).text() == "取消"

def test_annotation_page_picture_list_marks_annotated_images(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    import json

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AnnotationPage

    images_dir = tmp_path / "images"
    labels_dir = tmp_path / "images"
    images_dir.mkdir(exist_ok=True)
    from PIL import Image

    Image.new("RGB", (32, 32), "white").save(images_dir / "1.jpg")
    Image.new("RGB", (32, 32), "white").save(images_dir / "2.jpg")
    (labels_dir / "1.json").write_text(
        json.dumps(
            {
                "imagePath": "1.jpg",
                "imageWidth": 32,
                "imageHeight": 32,
                "shapes": [
                    {
                        "label": "weld",
                        "points": [[1, 1], [10, 10]],
                        "shape_type": "rectangle",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )

    page = _show_annotation_page(AnnotationPage(fake_app), app)
    first_item = page.file_list.item(0)
    second_item = page.file_list.item(1)
    first_widget = page.file_list.itemWidget(first_item)
    second_widget = page.file_list.itemWidget(second_item)

    assert first_widget.__class__.__name__ == "AnnotationFileListItemWidget"
    assert second_widget.__class__.__name__ == "AnnotationFileListItemWidget"
    assert first_widget.text() == "1.jpg"
    assert second_widget.text() == "2.jpg"
    assert first_item.text() == ""
    assert second_item.text() == ""
    assert first_widget.checkbox.isEnabled() is True
    assert second_widget.checkbox.isEnabled() is True
    assert first_widget.isChecked() is True
    assert second_widget.isChecked() is False

def test_annotation_page_prepare_for_first_show_keeps_followup_rendering(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AnnotationPage

    images_dir = tmp_path / "images"
    images_dir.mkdir()
    from PIL import Image

    for index in range(1, 26):
        Image.new("RGB", (32, 32), "white").save(images_dir / f"{index}.jpg")

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )

    page = AnnotationPage(fake_app)

    page.prepare_for_first_show()

    assert len(page.image_items) == 25
    assert page.current_index == 0
    assert page.current_image_path == images_dir / "1.jpg"
    assert page.file_list.count() == 20
    assert page._file_list_render_timer.isActive() is True
