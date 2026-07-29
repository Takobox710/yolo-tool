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



def test_annotation_canvas_escape_clears_selection_in_edit_mode():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.annotation import EditableAnnotation
    from src.shared.qt import Qt
    from src.ui.features.annotation.canvas.widget import AnnotationCanvas

    canvas = AnnotationCanvas()
    canvas.annotations = [
        EditableAnnotation(0, "rect", [(1.0, 1.0), (10.0, 1.0), (10.0, 10.0), (1.0, 10.0)])
    ]
    canvas.selected_index = 0
    canvas.hovered_index = 0

    canvas.keyPressEvent(type("EscapeEvent", (), {"key": lambda self: Qt.Key.Key_Escape})())

    assert canvas.selected_index == -1
    assert canvas.hovered_index == -1



def test_annotation_canvas_rect_crosshair_only_tracks_manual_mode():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtCore import QPointF
    from src.shared.qt import QApplication
    from src.ui.features.annotation.canvas.widget import AnnotationCanvas

    app = QApplication.instance() or QApplication([])
    canvas = AnnotationCanvas()
    canvas.set_draw_shape("rect")

    canvas.set_crosshair_position(QPointF(80.0, 60.0))
    assert canvas.crosshair_position == (80.0, 60.0)

    canvas.set_sam_assist_enabled(True)
    assert canvas.crosshair_position is None

    canvas.set_crosshair_position(QPointF(100.0, 90.0))
    assert canvas.crosshair_position is None

    canvas.set_sam_assist_enabled(False)
    canvas.set_crosshair_position(QPointF(120.0, 110.0))
    assert canvas.crosshair_position == (120.0, 110.0)



def test_oriented_rectangle_has_four_edge_rotation_handles():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.annotation import EditableAnnotation
    from src.shared.qt import QApplication
    from src.ui.features.annotation.canvas.widget import AnnotationCanvas

    app = QApplication.instance() or QApplication([])
    canvas = AnnotationCanvas()
    annotation = EditableAnnotation(
        0,
        "obb",
        [(0.0, 0.0), (100.0, 0.0), (100.0, 60.0), (0.0, 60.0)],
    )

    handles = canvas._annotation_handles(annotation)
    canvas.annotations = [annotation]

    assert [handle for handle, _point in handles if handle.startswith("rotate-")] == [
        "rotate-0",
        "rotate-1",
        "rotate-2",
        "rotate-3",
    ]
    assert [point for handle, point in handles if handle.startswith("rotate-")] == [
        (50.0, 0.0),
        (100.0, 30.0),
        (50.0, 60.0),
        (0.0, 30.0),
    ]
    assert canvas._hit_annotation_handle((100.0, 30.0), 0) == ("rotate", 1)



def test_oriented_rectangle_edge_handle_rotates_around_center():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from pytest import approx
    from src.services.annotation import EditableAnnotation
    from src.shared.qt import QApplication
    from src.ui.features.annotation.canvas.widget import AnnotationCanvas

    app = QApplication.instance() or QApplication([])
    canvas = AnnotationCanvas()
    canvas.annotations = [
        EditableAnnotation(
            0,
            "obb",
            [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)],
        )
    ]
    canvas.selected_index = 0
    canvas.active_handle = ("rotate", 0)

    canvas._update_selected_handle((10.0, 5.0))

    expected_points = [
        (10.0, 0.0),
        (10.0, 10.0),
        (0.0, 10.0),
        (0.0, 0.0),
    ]
    assert all(actual == approx(expected) for actual, expected in zip(canvas.annotations[0].points, expected_points))



def test_optimized_mirror_rectangle_uses_centerline_and_width_handles():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.annotation import EditableAnnotation
    from src.shared.qt import QApplication
    from src.ui.features.annotation.canvas.widget import AnnotationCanvas

    app = QApplication.instance() or QApplication([])
    canvas = AnnotationCanvas()
    canvas.optimize_mirror_edit = True
    annotation = EditableAnnotation(
        0,
        "obb_mirror",
        [(20.0, 40.0), (80.0, 40.0), (80.0, 60.0), (20.0, 60.0)],
    )
    canvas.annotations = [annotation]

    handles = canvas._annotation_handles(annotation)

    assert [handle for handle, _point in handles] == [
        "mirror-center-0",
        "mirror-center-1",
        "mirror-width-0",
        "mirror-width-1",
    ]
    assert [point for _handle, point in handles] == [
        (20.0, 50.0),
        (80.0, 50.0),
        (50.0, 40.0),
        (50.0, 60.0),
    ]
    assert canvas._hit_annotation_handle((50.0, 40.0), 0) == ("mirror-width", 0)

    canvas.selected_index = 0
    canvas.active_handle = ("mirror-width", 0)
    canvas._update_selected_handle((50.0, 30.0))

    assert canvas.annotations[0].points == [
        (20.0, 30.0),
        (80.0, 30.0),
        (80.0, 70.0),
        (20.0, 70.0),
    ]

    canvas.annotations[0].points = [
        (20.0, 40.0),
        (80.0, 40.0),
        (80.0, 60.0),
        (20.0, 60.0),
    ]
    canvas.active_handle = ("mirror-center", 0)
    canvas._update_selected_handle((10.0, 50.0))

    assert canvas.annotations[0].points == [
        (10.0, 40.0),
        (80.0, 40.0),
        (80.0, 60.0),
        (10.0, 60.0),
    ]



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



