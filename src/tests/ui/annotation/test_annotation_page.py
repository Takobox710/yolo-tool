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
        optimize_mirror_edit=True,
    )

    assert dialog.optimize_mirror_check.isChecked() is True
    assert dialog.values()[-1] is True


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
            },
        )
    ]


def test_draw_shape_dialog_disables_unsupported_shapes_when_sam_enabled(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.annotation.sam_assist import sam_model_spec_from_path
    from src.shared.qt import QApplication, QLabel
    from src.ui.features.annotation.dialogs import DrawShapeDialog

    app = QApplication.instance() or QApplication([])
    spec = sam_model_spec_from_path(tmp_path / "sam2.1_hiera_base_plus.pt")
    dialog = DrawShapeDialog(
        True,
        sam_models=[spec],
        selected_sam_model=spec.key,
        sam_enabled=True,
    )

    assert dialog.sam_switch.isChecked() is True
    assert dialog.selected_sam_model == spec.key
    assert dialog._shape_buttons["rect"].isEnabled() is True
    assert dialog._shape_buttons["obb_single"].isEnabled() is True
    assert dialog._shape_buttons["polygon"].isEnabled() is True
    assert dialog._shape_buttons["circle"].isEnabled() is False
    assert dialog._shape_buttons["obb_mirror"].isEnabled() is True
    assert dialog._shape_buttons["line_expand"].isEnabled() is False
    assert not any(
        label.text() == "请选择要绘制的标注类型"
        for label in dialog.findChildren(QLabel)
    )


def test_draw_shape_dialog_applies_sam_switch_and_model_immediately(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.annotation.sam_assist import sam_model_spec_from_path
    from src.shared.qt import QApplication
    from src.ui.features.annotation.dialogs import DrawShapeDialog

    app = QApplication.instance() or QApplication([])
    first = sam_model_spec_from_path(tmp_path / "sam2.1_hiera_base_plus.pt")
    second = sam_model_spec_from_path(tmp_path / "sam2.1_hiera_small.pt")
    toggles = []
    models = []
    dialog = DrawShapeDialog(
        False,
        sam_models=[first, second],
        selected_sam_model=first.key,
        sam_toggle_callback=lambda enabled: toggles.append(enabled) or enabled,
        sam_model_callback=models.append,
    )

    dialog.sam_switch.click()
    dialog.sam_model_combo.setCurrentIndex(1)

    assert toggles == [True]
    assert models == [second.key]
    assert dialog.sam_enabled is True
    assert dialog._shape_buttons["circle"].isEnabled() is False


def test_sam_assist_icon_loads_from_qt_resource():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.shared.qt import QApplication
    from src.ui.shared.assets import load_sam_assist_icon

    app = QApplication.instance() or QApplication([])

    assert load_sam_assist_icon().isNull() is False


def test_annotation_canvas_sam_preview_confirms_without_manual_drawing():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtGui import QMouseEvent, QPointingDevice, QPixmap
    from src.shared.qt import QApplication, QEvent, Qt
    from src.ui.features.annotation.canvas.widget import AnnotationCanvas

    app = QApplication.instance() or QApplication([])
    canvas = AnnotationCanvas()
    canvas.resize(420, 360)
    canvas.pixmap = QPixmap(100, 100)
    canvas.image_size = (100, 100)
    canvas.set_draw_shape("circle")
    canvas.set_sam_assist_enabled(True)
    assert canvas.draw_shape == "rect"
    canvas.set_sam_preview(
        "rect",
        {
            "rectangle": [[10, 10], [40, 10], [40, 50], [10, 50]],
            "polygon": [],
            "oriented_rectangle": [],
        },
        1,
    )
    changed = []
    canvas.changed_callback = lambda: changed.append(True)
    position = canvas._image_to_widget((20.0, 20.0))
    event = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        position,
        position,
        position,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        QPointingDevice.primaryPointingDevice(),
    )

    canvas.mousePressEvent(event)

    assert len(canvas.annotations) == 1
    assert canvas.annotations[0].shape == "rect"
    assert canvas.annotations[0].points == [(10.0, 10.0), (40.0, 10.0), (40.0, 50.0), (10.0, 50.0)]
    assert changed == [True]
    assert canvas.drag_start is None


def test_annotation_canvas_sam_preview_supports_mirror_obb():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtGui import QMouseEvent, QPointingDevice, QPixmap
    from src.shared.qt import QApplication, QEvent, Qt
    from src.ui.features.annotation.canvas.widget import AnnotationCanvas

    app = QApplication.instance() or QApplication([])
    canvas = AnnotationCanvas()
    canvas.resize(420, 360)
    canvas.pixmap = QPixmap(100, 100)
    canvas.image_size = (100, 100)
    canvas.set_draw_shape("obb_mirror")
    canvas.set_sam_assist_enabled(True)
    canvas.set_sam_preview(
        "obb_mirror",
        {
            "rectangle": [],
            "polygon": [],
            "oriented_rectangle": [[20, 30], [60, 20], [70, 50], [30, 60]],
        },
        1,
    )
    position = canvas._image_to_widget((45.0, 35.0))
    event = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        position,
        position,
        position,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        QPointingDevice.primaryPointingDevice(),
    )

    canvas.mousePressEvent(event)

    assert len(canvas.annotations) == 1
    assert canvas.annotations[0].shape == "obb_mirror"
    assert canvas.annotations[0].points == [
        (20.0, 30.0),
        (60.0, 20.0),
        (70.0, 50.0),
        (30.0, 60.0),
    ]


def test_annotation_canvas_sam_without_preview_requests_hover_and_blocks_manual_draw():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtGui import QMouseEvent, QPointingDevice, QPixmap
    from src.shared.qt import QApplication, QEvent, Qt
    from src.ui.features.annotation.canvas.widget import AnnotationCanvas

    app = QApplication.instance() or QApplication([])
    canvas = AnnotationCanvas()
    canvas.resize(420, 360)
    canvas.pixmap = QPixmap(100, 100)
    canvas.image_size = (100, 100)
    canvas.set_draw_shape("polygon")
    canvas.set_sam_assist_enabled(True)
    requests = []
    canvas.sam_hover_callback = lambda point, shape: requests.append((point, shape))
    position = canvas._image_to_widget((50.0, 50.0))
    event = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        position,
        position,
        position,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        QPointingDevice.primaryPointingDevice(),
    )

    canvas.mousePressEvent(event)

    assert requests == [((50.0, 50.0), "polygon")]
    assert canvas.annotations == []
    assert canvas.polygon_points == []
    assert canvas.drag_start is None


def test_sam_runtime_worker_keeps_only_latest_waiting_prediction():
    from src.ui.features.annotation.sam.runtime import SamAssistRuntimeWorker

    worker = SamAssistRuntimeWorker()
    sent = []

    def fake_send(action, payload):
        sent.append((action, dict(payload)))
        return f"request-{len(sent)}"

    worker._send = fake_send
    worker._handle_command("predict_point", {"x": 1})
    worker._handle_command("predict_point", {"x": 2})
    worker._handle_command("predict_point", {"x": 3})

    assert sent == [("predict_point", {"x": 1})]
    worker._prediction_request_id = ""
    worker._send_latest_prediction()
    assert sent == [
        ("predict_point", {"x": 1}),
        ("predict_point", {"x": 3}),
    ]


def test_sam_controller_adapts_movement_without_waiting_for_mouse_stop(tmp_path):
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
    controller = page.sam_assist
    sent = []
    controller.enabled = True
    controller.state = "ready"
    controller.model_generation = 2
    controller.image_generation = 3
    controller._worker = SimpleNamespace(predict_point=lambda payload: sent.append(payload))

    controller.request_hover((10.0, 11.0), "rect")
    controller.request_hover((20.0, 21.0), "rect")
    controller.request_hover((30.0, 31.0), "rect")
    controller.request_hover((30.5, 31.0), "rect")

    assert [(item["x"], item["y"]) for item in sent] == [(10.0, 11.0)]
    assert controller._hover_inflight is True
    assert controller._hover_timer.isActive() is False
    assert controller._hover_payload["x"] == 30.0

    controller._last_hover_submit_at -= 1.0
    controller._finish_hover_request()

    assert [(item["x"], item["y"]) for item in sent] == [
        (10.0, 11.0),
        (30.0, 31.0),
    ]
    assert controller._hover_inflight is True

    controller._hover_ema_ms = 30.0
    assert controller._hover_interval_ms() == 50
    controller._hover_ema_ms = 100.0
    assert controller._hover_interval_ms() == 75
    controller._hover_ema_ms = 300.0
    assert controller._hover_interval_ms() == 120


def test_sam_controller_displays_latest_completed_frame_while_mouse_moves(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.annotation import EditableAnnotation
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
    controller = page.sam_assist
    page.canvas.set_draw_shape("rect")
    controller.enabled = True
    controller.state = "predicting"
    controller.model_generation = 4
    controller.image_generation = 5
    controller.hover_generation = 7
    page.canvas.sam_preview_annotation = EditableAnnotation(
        0,
        "rect",
        [(1.0, 1.0), (2.0, 1.0), (2.0, 2.0), (1.0, 2.0)],
    )

    controller._handle_response(
        "predict_point",
        {
            "model_generation": 4,
            "image_generation": 5,
            "hover_generation": 6,
            "shape": "rect",
        },
        {
            "geometry": {
                "rectangle": [[10, 10], [40, 10], [40, 40], [10, 40]],
            }
        },
    )

    assert page.canvas.sam_preview_generation == 6
    assert page.canvas.sam_preview_annotation.points[0] == (10.0, 10.0)
    assert controller.state == "predicting"


def test_sam_toggle_off_keeps_runtime_until_page_shutdown(tmp_path):
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
    controller = page.sam_assist

    class FakeWorker:
        def __init__(self):
            self.shutdown_calls = 0

        def shutdown(self):
            self.shutdown_calls += 1

    worker = FakeWorker()
    controller.enabled = True
    controller._worker = worker
    controller._model_loaded = True
    controller._image_ready = True

    assert controller.set_enabled(False) is False
    assert controller._worker is worker
    assert worker.shutdown_calls == 0

    assert controller.set_enabled(True) is True
    assert controller._worker is worker
    assert worker.shutdown_calls == 0

    controller.shutdown(wait=False)
    assert worker.shutdown_calls == 1


def test_sam_runtime_worker_requests_graceful_shutdown_before_stop(monkeypatch):
    from src.ui.features.annotation.sam.runtime import SamAssistRuntimeWorker
    import src.ui.features.annotation.sam.runtime as sam_runtime

    writes = []
    stops = []

    class FakeStdin:
        def write(self, value):
            writes.append(value)

        def flush(self):
            return None

    class FakeProcess:
        stdin = FakeStdin()

        def poll(self):
            return None

        def wait(self, timeout):
            assert timeout == 0.75
            return 0

    handle = SimpleNamespace(process=FakeProcess())
    worker = SamAssistRuntimeWorker()
    worker._handle = handle
    monkeypatch.setattr(sam_runtime, "stop_process", lambda current: stops.append(current))

    worker._handle_command("shutdown", {})

    assert worker._shutdown_requested is True
    assert len(writes) == 1
    assert '"action": "shutdown"' in writes[0]
    assert stops == [handle]


def test_sam_controller_ignores_stale_worker_and_hover_failures(tmp_path):
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
    controller = page.sam_assist
    current_worker = object()
    stale_worker = object()
    controller.enabled = True
    controller.state = "predicting"
    controller._worker = current_worker
    controller.model_generation = 4
    controller.image_generation = 5
    controller.hover_generation = 6

    controller._handle_runtime_failure(
        "old worker failed",
        worker=stale_worker,
        model_generation=3,
    )
    controller._handle_request_failure(
        "predict_point",
        {
            "model_generation": 4,
            "image_generation": 5,
            "hover_generation": 5,
        },
        "old hover failed",
    )

    assert controller.enabled is True
    assert controller.state == "predicting"


def test_sam_model_reload_clears_preview_and_pending_hover(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.annotation import EditableAnnotation
    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AnnotationPage
    import src.ui.features.annotation.sam.controller as sam_controller

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )
    page = AnnotationPage(fake_app)
    controller = page.sam_assist

    class FakeWorker:
        def __init__(self, _parent):
            self.response_received = SimpleNamespace(connect=lambda _callback: None)
            self.request_failed = SimpleNamespace(connect=lambda _callback: None)
            self.runtime_failed = SimpleNamespace(connect=lambda _callback: None)
            self.log_received = SimpleNamespace(connect=lambda _callback: None)
            self.finished = SimpleNamespace(connect=lambda _callback: None)

        def start(self):
            return None

        def load_model(self, _payload):
            return None

    monkeypatch.setattr(sam_controller, "SamAssistRuntimeWorker", FakeWorker)
    controller.enabled = True
    controller._hover_payload = {"x": 1.0}
    controller._hover_timer.start()
    page.canvas.sam_preview_annotation = EditableAnnotation(
        0,
        "rect",
        [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)],
    )

    controller._load_selected_model()

    assert controller._hover_payload is None
    assert controller._hover_timer.isActive() is False
    assert page.canvas.sam_preview_annotation is None


def test_sam_controller_cancel_hover_invalidates_inflight_result(tmp_path):
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
    controller = page.sam_assist
    page.canvas.set_draw_shape("rect")
    controller.enabled = True
    controller.state = "predicting"
    controller.hover_generation = 8
    controller._hover_payload = {"hover_generation": 8}
    controller._hover_timer.start()

    controller.cancel_hover()

    assert controller.hover_generation == 9
    assert controller._hover_payload is None
    assert controller._hover_timer.isActive() is False
    assert controller.state == "ready"

    controller._handle_response(
        "predict_point",
        {
            "model_generation": controller.model_generation,
            "image_generation": controller.image_generation,
            "hover_generation": 8,
            "shape": "rect",
        },
        {
            "geometry": {
                "rectangle": [[10, 10], [40, 10], [40, 40], [10, 40]],
            }
        },
    )

    assert page.canvas.sam_preview_annotation is None


def _mouse_event(viewport, event_type, pos, button, buttons):
    from src.shared.qt import Qt
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QMouseEvent, QPointingDevice

    local_pos = QPointF(pos)
    scene_pos = QPointF(pos)
    global_pos = QPointF(viewport.mapToGlobal(pos))
    return QMouseEvent(
        event_type,
        local_pos,
        scene_pos,
        global_pos,
        button,
        buttons,
        Qt.KeyboardModifier.NoModifier,
        QPointingDevice.primaryPointingDevice(),
    )


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
    from src.shared.qt import QApplication
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
    dialog.model_combo.setCurrentText(str(model_path))
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
    assert all(check.isChecked() for check in dialog.sam3_checks)
    dialog.close()


def test_annotation_page_adds_all_project_labelme_categories(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    import json

    from PIL import Image
    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AnnotationPage

    images_dir = tmp_path / "images"
    images_dir.mkdir()
    Image.new("RGB", (32, 32), "white").save(images_dir / "1.jpg")
    (images_dir / "1.json").write_text(
        json.dumps({"shapes": [{"label": "weld"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (images_dir / "other.json").write_text(
        json.dumps({"shapes": [{"label": "scratch"}]}, ensure_ascii=False),
        encoding="utf-8",
    )

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )

    _show_annotation_page(AnnotationPage(fake_app), app)

    assert settings.dataset.class_names == ["weld", "scratch"]


def test_class_manager_blocks_deleting_used_category(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.shared.qt import QApplication, QMessageBox
    from src.ui.features.annotation.dialogs import ClassManagerDialog

    app = QApplication.instance() or QApplication([])
    dialog = ClassManagerDialog(
        ["weld", "scratch"],
        annotation_counts=[2, 0],
    )
    dialog.listing.setCurrentRow(0)
    messages = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda _parent, _title, message: messages.append(message),
    )

    dialog.delete_class()

    assert dialog.class_names == ["weld", "scratch"]
    assert messages == ["你有 2 个标注依赖此类别名，无法删除。"]


def test_class_manager_converts_category_indices(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.annotation import EditableAnnotation
    from src.shared.qt import QApplication
    from src.ui.features.annotation.dialogs import ClassManagerDialog

    app = QApplication.instance() or QApplication([])
    dialog = ClassManagerDialog(
        ["weld", "scratch"],
        annotations=[
            EditableAnnotation(0, "rect", []),
            EditableAnnotation(0, "rect", []),
            EditableAnnotation(1, "rect", []),
        ],
    )
    dialog.convert_classes(0, 1)

    assert dialog.annotation_class_ids == [1, 1, 1]
    assert dialog.annotation_class_ids_changed is True


def test_class_conversion_dialog_confirms_selected_categories(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.shared.qt import QApplication, QDialog, QDialogButtonBox
    from src.ui.features.annotation.dialogs import ClassConversionDialog

    app = QApplication.instance() or QApplication([])
    dialog = ClassConversionDialog(["weld", "scratch"], [2, 1])
    dialog.source_combo.setCurrentIndex(0)
    dialog.target_combo.setCurrentIndex(1)

    buttons = dialog.findChild(QDialogButtonBox)
    assert buttons is not None
    buttons.button(QDialogButtonBox.StandardButton.Ok).click()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.values() == (0, 1)
    assert dialog.count_label.text() == "当前源类别包含 2 个标注。"

    cancelled = ClassConversionDialog(["weld", "scratch"], [2, 1])
    cancel_buttons = cancelled.findChild(QDialogButtonBox)
    assert cancel_buttons is not None
    cancel_buttons.button(QDialogButtonBox.StandardButton.Cancel).click()
    assert cancelled.result() == QDialog.DialogCode.Rejected


def test_class_manager_conversion_button_opens_independent_dialog(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.shared.qt import QApplication, QDialog
    from src.ui.features.annotation import dialogs as annotation_dialogs
    from src.ui.features.annotation.dialogs import ClassManagerDialog

    app = QApplication.instance() or QApplication([])
    manager = ClassManagerDialog(["weld", "scratch"], annotation_counts=[2, 0])
    calls = []

    class FakeConversionDialog:
        def __init__(self, class_names, annotation_counts, parent):
            calls.append((class_names, annotation_counts, parent))

        def exec(self):
            return QDialog.DialogCode.Rejected

    monkeypatch.setattr(annotation_dialogs, "ClassConversionDialog", FakeConversionDialog)
    manager.convert_button.click()

    assert calls == [(["weld", "scratch"], [2, 0], manager)]
