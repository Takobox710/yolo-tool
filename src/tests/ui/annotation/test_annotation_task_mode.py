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


def test_annotation_page_exposes_seg_task_type(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AnnotationPage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )
    page = AnnotationPage(fake_app)

    assert [
        page.output_mode_combo.itemText(index)
        for index in range(page.output_mode_combo.count())
    ] == ["detect", "obb", "seg"]

    page.output_mode_combo.setCurrentText("seg")
    assert page.output_mode == "seg"
    assert settings.task.mode == "seg"




def test_annotation_page_hides_yolo_task_controls_until_yolo_setting_enabled(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AnnotationPage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )
    page = AnnotationPage(fake_app)

    assert page.output_mode_label.isHidden()
    assert page.output_mode_combo.isHidden()
    settings.annotation.show_yolo_save_in_context_menu = True
    page._refresh_task_mode_controls()

    assert page.output_mode_label.isHidden() is False
    assert page.output_mode_combo.isHidden() is False
    assert page.output_mode_combo.currentIndex() == -1
    assert "C62828" in page.output_mode_combo.styleSheet()




def test_annotation_page_detects_global_yolo_mode_and_keeps_it_across_images(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PIL import Image
    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AnnotationPage

    images = tmp_path / "images"
    labels = tmp_path / "labels"
    images.mkdir()
    labels.mkdir()
    Image.new("RGB", (32, 32), "white").save(images / "1.jpg")
    Image.new("RGB", (32, 32), "white").save(images / "2.jpg")
    for name in ("1.txt", "2.txt"):
        (labels / name).write_text("0 0 0 1 0 1 1 0 1\n", encoding="utf-8")

    settings = build_default_settings(tmp_path)
    settings.paths.images_dir = str(images)
    settings.paths.labels_dir = str(labels)
    settings.annotation.show_yolo_save_in_context_menu = True
    app = QApplication.instance() or QApplication([])
    page = _show_annotation_page(
        AnnotationPage(
            SimpleNamespace(
                settings=settings,
                settings_service=SimpleNamespace(save=lambda _data: None),
            )
        ),
        app,
    )

    assert page.output_mode == "obb"
    assert settings.task.mode_selected is True
    page.change_current_index(1)
    assert page.output_mode == "obb"




def test_annotation_page_empty_yolo_file_keeps_task_unselected_and_disables_yolo_save(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PIL import Image
    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AnnotationPage

    images = tmp_path / "images"
    labels = tmp_path / "labels"
    images.mkdir()
    labels.mkdir()
    Image.new("RGB", (32, 32), "white").save(images / "1.jpg")
    (labels / "1.txt").write_text("\n", encoding="utf-8")
    settings = build_default_settings(tmp_path)
    settings.paths.images_dir = str(images)
    settings.paths.labels_dir = str(labels)
    settings.annotation.show_yolo_save_in_context_menu = True
    app = QApplication.instance() or QApplication([])
    page = _show_annotation_page(
        AnnotationPage(
            SimpleNamespace(
                settings=settings,
                settings_service=SimpleNamespace(save=lambda _data: None),
            )
        ),
        app,
    )

    assert page.output_mode is None
    assert page.output_mode_combo.currentIndex() == -1
    assert page.canvas.can_save_yolo is False




def test_annotation_page_yolo_fallback_read_is_controlled_by_setting(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PIL import Image
    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AnnotationPage

    images = tmp_path / "images"
    labels = tmp_path / "labels"
    images.mkdir()
    labels.mkdir()
    Image.new("RGB", (32, 32), "white").save(images / "1.jpg")
    (labels / "1.txt").write_text("0 0.5 0.5 0.2 0.2\n", encoding="utf-8")
    settings = build_default_settings(tmp_path)
    settings.paths.images_dir = str(images)
    settings.paths.labels_dir = str(labels)
    settings.annotation.show_yolo_save_in_context_menu = True
    app = QApplication.instance() or QApplication([])
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )
    page = _show_annotation_page(AnnotationPage(fake_app), app)
    assert page.output_mode == "detect"
    assert page.canvas.annotations == []

    settings.annotation.load_yolo_when_labelme_missing = True
    page.load_current()
    assert len(page.canvas.annotations) == 1
    assert page.canvas.annotations[0].shape == "rect"




def test_annotation_page_task_mode_refreshes_annotation_list_immediately(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.annotation import EditableAnnotation
    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AnnotationPage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    settings.dataset.class_names = ["weld"]
    settings.annotation.show_yolo_save_in_context_menu = True
    settings.task.mode = "detect"
    settings.task.mode_selected = True
    page = AnnotationPage(
        SimpleNamespace(
            settings=settings,
            settings_service=SimpleNamespace(save=lambda _data: None),
        )
    )
    page.canvas.annotations = [
        EditableAnnotation(0, "obb_mirror", [(1, 1), (10, 1), (10, 10), (1, 10)])
    ]
    page.refresh_annotation_list()
    assert "（detect）" in page.annotation_list.item(0).text()

    page.output_mode_combo.setCurrentText("obb")
    assert "（obb）" in page.annotation_list.item(0).text()




def test_annotation_page_reports_independent_labelme_and_yolo_unsaved_states(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PIL import Image
    from src.services.annotation import EditableAnnotation
    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AnnotationPage

    images = tmp_path / "images"
    images.mkdir()
    Image.new("RGB", (32, 32), "white").save(images / "1.jpg")
    settings = build_default_settings(tmp_path)
    settings.paths.images_dir = str(images)
    settings.annotation.auto_save = False
    settings.annotation.auto_convert_yolo = False
    settings.annotation.show_yolo_save_in_context_menu = True
    settings.task.mode = "detect"
    settings.task.mode_selected = True
    app = QApplication.instance() or QApplication([])
    page = _show_annotation_page(
        AnnotationPage(
            SimpleNamespace(
                settings=settings,
                settings_service=SimpleNamespace(save=lambda _data: None),
            )
        ),
        app,
    )
    page.canvas.annotations = [
        EditableAnnotation(0, "rect", [(1, 1), (10, 1), (10, 10), (1, 10)])
    ]
    page.mark_dirty_and_save()
    assert page._current_image_unsaved_text() == "两种格式标注均未保存"

    page.save_current_labelme()
    assert page._current_image_unsaved_text() == "YOLO标注未保存"
    page.save_current_yolo()
    assert page._current_image_unsaved_text() == ""




def test_annotation_canvas_selection_does_not_commit_a_change():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.annotation import EditableAnnotation
    from src.shared.qt import QApplication
    from src.ui.features.annotation.canvas.widget import AnnotationCanvas

    app = QApplication.instance() or QApplication([])
    canvas = AnnotationCanvas()
    canvas.annotations = [
        EditableAnnotation(0, "rect", [(0, 0), (10, 0), (10, 10), (0, 10)])
    ]
    changed = []
    history = []
    canvas.changed_callback = lambda: changed.append(True)
    canvas.history_callback = lambda *args: history.append(args)

    before = canvas._snapshot_annotations()
    canvas._begin_annotation_mutation(0)
    canvas.selected_index = 0
    canvas._emit_annotation_mutation(before, 0)

    assert changed == []
    assert history == []




def test_annotation_page_undo_redo_restores_created_annotation_and_selects_it(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PIL import Image
    from src.services.annotation import EditableAnnotation
    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AnnotationPage

    images = tmp_path / "images"
    images.mkdir()
    Image.new("RGB", (32, 32), "white").save(images / "1.jpg")
    settings = build_default_settings(tmp_path)
    settings.paths.images_dir = str(images)
    app = QApplication.instance() or QApplication([])
    page = _show_annotation_page(
        AnnotationPage(
            SimpleNamespace(
                settings=settings,
                settings_service=SimpleNamespace(save=lambda _data: None),
            )
        ),
        app,
    )

    page.canvas._finish_annotation(
        EditableAnnotation(0, "rect", [(1, 1), (10, 1), (10, 10), (1, 10)])
    )
    assert page.canvas.can_undo is True

    page.undo_annotation_change()
    assert page.canvas.annotations == []
    assert page.canvas.selected_index == -1
    assert page.canvas.can_redo is True

    page.redo_annotation_change()
    assert len(page.canvas.annotations) == 1
    assert page.canvas.selected_index == 0




def test_annotation_page_history_is_cross_image_and_new_edit_clears_redo(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PIL import Image
    from src.services.annotation import EditableAnnotation
    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AnnotationPage

    images = tmp_path / "images"
    images.mkdir()
    for name in ("1.jpg", "2.jpg"):
        Image.new("RGB", (32, 32), "white").save(images / name)
    settings = build_default_settings(tmp_path)
    settings.paths.images_dir = str(images)
    app = QApplication.instance() or QApplication([])
    page = _show_annotation_page(
        AnnotationPage(
            SimpleNamespace(
                settings=settings,
                settings_service=SimpleNamespace(save=lambda _data: None),
            )
        ),
        app,
    )

    page.canvas._finish_annotation(
        EditableAnnotation(0, "rect", [(1, 1), (10, 1), (10, 10), (1, 10)])
    )
    page.next_image()
    page.canvas._finish_annotation(
        EditableAnnotation(0, "rect", [(2, 2), (11, 2), (11, 11), (2, 11)])
    )

    page.undo_annotation_change()
    assert page.current_index == 1
    assert page.canvas.annotations == []
    page.undo_annotation_change()
    assert page.current_index == 0
    assert page.canvas.annotations == []

    page.redo_annotation_change()
    assert page.current_index == 0
    assert len(page.canvas.annotations) == 1
    page.canvas._finish_annotation(
        EditableAnnotation(0, "rect", [(3, 3), (12, 3), (12, 12), (3, 12)])
    )
    assert page.canvas.can_redo is False


