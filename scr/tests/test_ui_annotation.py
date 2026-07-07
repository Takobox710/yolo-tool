from pathlib import Path

import os

import subprocess

import sys

from types import SimpleNamespace

from scr.tests.helpers.ui_paths import (
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


def test_annotation_page_uses_picture_list_header_and_count(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication, QLabel
    from scr.ui.views.annotation import AnnotationPage

    images_dir = tmp_path / "images"
    images_dir.mkdir()
    from PIL import Image

    Image.new("RGB", (32, 32), "white").save(images_dir / "1.jpg")
    Image.new("RGB", (32, 32), "white").save(images_dir / "2.jpg")

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )

    page = AnnotationPage(fake_app)
    labels = [label.text() for label in page.findChildren(QLabel)]

    assert "图片列表：" in labels
    assert page.file_count_label.text() == "1/2"


def test_annotation_page_picture_list_marks_annotated_images(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    import json

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication
    from scr.ui.views.annotation import AnnotationPage

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

    page = AnnotationPage(fake_app)
    first_widget = page.file_list.itemWidget(page.file_list.item(0))
    second_widget = page.file_list.itemWidget(page.file_list.item(1))

    assert first_widget.__class__.__name__ == "AnnotationFileListItemWidget"
    assert second_widget.__class__.__name__ == "AnnotationFileListItemWidget"
    assert first_widget.text() == "1.jpg"
    assert second_widget.text() == "2.jpg"
    assert first_widget.isChecked() is True
    assert second_widget.isChecked() is False


def test_annotation_page_delete_selected_updates_current_checkbox_without_full_refresh(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    import json

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication
    from scr.ui.views.annotation import AnnotationPage

    images_dir = tmp_path / "images"
    images_dir.mkdir()
    from PIL import Image

    Image.new("RGB", (32, 32), "white").save(images_dir / "1.jpg")
    (images_dir / "1.json").write_text(
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

    page = AnnotationPage(fake_app)
    first_item = page.file_list.item(0)
    first_widget = page.file_list.itemWidget(first_item)

    assert first_widget.__class__.__name__ == "AnnotationFileListItemWidget"
    assert first_widget.isChecked() is True
    assert len(page.canvas.annotations) == 1

    def fail_refresh_file_list():
        raise AssertionError("delete_selected should not rebuild the entire file list")

    page.refresh_file_list = fail_refresh_file_list
    page.canvas.selected_index = 0
    page.delete_selected()

    assert len(page.canvas.annotations) == 0
    assert first_widget.isChecked() is False


def test_annotation_canvas_cancel_action_only_shows_while_drawing():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.ui.views.annotation_canvas import AnnotationCanvas

    canvas = AnnotationCanvas()
    assert canvas._can_show_cancel_drawing_action() is False

    canvas.set_draw_shape("rect")
    assert canvas._can_show_cancel_drawing_action() is True

    canvas.set_draw_shape("select")
    assert canvas._can_show_cancel_drawing_action() is False

    canvas.drag_start = (10.0, 10.0)
    assert canvas._can_show_cancel_drawing_action() is True


def test_annotation_canvas_delete_action_only_available_when_annotation_selected():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.services.editable_annotation_service import EditableAnnotation
    from scr.ui.views.annotation_canvas import AnnotationCanvas

    canvas = AnnotationCanvas()
    assert canvas._has_selected_annotation() is False

    canvas.annotations = [
        EditableAnnotation(0, "rect", [(1.0, 1.0), (10.0, 1.0), (10.0, 10.0), (1.0, 10.0)])
    ]
    assert canvas._has_selected_annotation() is False

    canvas.selected_index = 0
    assert canvas._has_selected_annotation() is True


def test_annotation_page_canvas_context_save_flags_follow_auto_save_settings(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication
    from scr.ui.views.annotation import AnnotationPage

    images_dir = tmp_path / "images"
    images_dir.mkdir()
    from PIL import Image

    Image.new("RGB", (32, 32), "white").save(images_dir / "1.jpg")

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    settings["annotation"]["auto_save"] = False
    settings["annotation"]["auto_convert_yolo"] = False
    settings["annotation"]["show_yolo_save_in_context_menu"] = True
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )

    page = AnnotationPage(fake_app)
    assert page.canvas.can_save_default is False
    assert page.canvas.can_save_labelme is True
    assert page.canvas.can_save_yolo is True
    assert page.canvas.can_undo is False

    settings["annotation"]["auto_save"] = True
    page._refresh_manual_action_buttons()
    assert page.canvas.can_save_labelme is False
    assert page.canvas.can_save_yolo is True

    settings["annotation"]["auto_convert_yolo"] = True
    page._refresh_manual_action_buttons()
    assert page.canvas.can_save_labelme is False
    assert page.canvas.can_save_yolo is False


def test_annotation_page_canvas_context_uses_single_save_when_yolo_menu_disabled(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication
    from scr.ui.views.annotation import AnnotationPage

    images_dir = tmp_path / "images"
    images_dir.mkdir()
    from PIL import Image

    Image.new("RGB", (32, 32), "white").save(images_dir / "1.jpg")

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    settings["annotation"]["auto_save"] = False
    settings["annotation"]["auto_convert_yolo"] = False
    settings["annotation"]["show_yolo_save_in_context_menu"] = False
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )

    page = AnnotationPage(fake_app)
    assert page.canvas.can_save_default is True
    assert page.canvas.can_save_labelme is True
    assert page.canvas.can_save_yolo is False


def test_annotation_page_canvas_context_undo_flag_tracks_dirty_state(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication
    from scr.ui.views.annotation import AnnotationPage

    images_dir = tmp_path / "images"
    images_dir.mkdir()
    from PIL import Image

    Image.new("RGB", (32, 32), "white").save(images_dir / "1.jpg")

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    settings["annotation"]["auto_save"] = False
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )

    page = AnnotationPage(fake_app)
    assert page.canvas.can_undo is False

    page.dirty = True
    page._refresh_manual_action_buttons()

    assert page.canvas.can_undo is True


def test_annotation_page_marks_current_image_unsaved_when_labelme_auto_save_disabled(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication
    from scr.ui.views.annotation import AnnotationPage

    images_dir = tmp_path / "images"
    images_dir.mkdir()
    from PIL import Image

    Image.new("RGB", (32, 32), "white").save(images_dir / "1.jpg")

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    settings["annotation"]["auto_save"] = False
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )

    page = AnnotationPage(fake_app)
    widget = page.file_list.itemWidget(page.file_list.item(0))
    assert widget.isUnsaved() is False

    page.dirty = True
    page._update_current_file_list_item()

    assert widget.isUnsaved() is True


def test_annotation_page_context_delete_annotations_removes_label_files(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    import json

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication
    from scr.ui.views.annotation import AnnotationPage

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
    settings["paths"]["labels_dir"] = str(labels_dir)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )

    page = AnnotationPage(fake_app)
    page.clear_annotations_for_image(image_path)

    assert (images_dir / "1.json").exists() is False
    assert (labels_dir / "1.txt").exists() is False


def test_annotation_page_context_delete_image_removes_image_and_labels(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    import json

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication
    from scr.ui.views.annotation import AnnotationPage

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
    settings["paths"]["labels_dir"] = str(labels_dir)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )

    page = AnnotationPage(fake_app)
    page.delete_image_and_annotations(image_path)

    assert image_path.exists() is False
    assert (images_dir / "1.json").exists() is False
    assert (labels_dir / "1.txt").exists() is False


def test_ai_prelabel_dialog_uses_expected_range_count(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication
    from scr.ui.views.annotation import AiPrelabelDialog, AnnotationPage

    images_dir = tmp_path / "images"
    images_dir.mkdir()
    from PIL import Image

    Image.new("RGB", (32, 32), "white").save(images_dir / "1.jpg")
    Image.new("RGB", (32, 32), "white").save(images_dir / "2.jpg")

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )

    page = AnnotationPage(fake_app)
    dialog = AiPrelabelDialog(page)

    assert dialog.range_count_label.text() == "已选择 1 张图片"
    dialog.range_combo.setCurrentText("全部图片")
    assert dialog.range_count_label.text() == "已选择 2 张图片"


def test_annotation_canvas_two_click_rectangle_respects_quick_draw_setting():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.ui.views.annotation_canvas import AnnotationCanvas

    canvas = AnnotationCanvas()
    canvas.set_interaction_config(False, False)
    canvas.set_draw_shape("rect")

    canvas._handle_two_click_shape_click((10.0, 10.0))
    assert canvas.drag_start == (10.0, 10.0)
    assert len(canvas.annotations) == 0

    canvas._handle_two_click_shape_click((30.0, 30.0))
    assert len(canvas.annotations) == 1
    assert canvas.annotations[0].shape == "rect"
    assert canvas.draw_shape == "select"
    assert canvas.drag_start is None


def test_annotation_settings_dialog_adds_help_symbols_and_tooltips(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication
    from scr.ui.views.annotation import AnnotationPage
    from scr.ui.views.annotation_dialogs import AnnotationSettingsDialog

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )

    page = AnnotationPage(fake_app)
    dialog = AnnotationSettingsDialog(
        enabled=True,
        pixels=10,
        auto_save=True,
        auto_convert_yolo=False,
        show_yolo_save_in_context_menu=False,
        continuous_draw=False,
        quick_draw=True,
        yolo_dir=str(tmp_path / "labels"),
        parent=page,
    )

    assert dialog.continuous_draw_check.text() == "开启连续标注 ⓘ"
    assert dialog.continuous_draw_check.toolTip() == "开启后完成一个标注会继续保持当前绘制类型；关闭后每次完成标注都会自动回到选择模式。"
    assert dialog.quick_draw_check.text() == "开启快捷标注 ⓘ"
    assert dialog.quick_draw_check.toolTip() == "开启后矩形框、圆形、直线扩展支持拖动后松开直接完成；关闭后改为通过多次点击确认。"
    assert dialog.show_yolo_context_check.text() == "右键显示保存YOLO标注 ⓘ"
    assert dialog.show_yolo_context_check.toolTip() == "开启后主界面右键菜单按需分别显示“保存Labelme标注”和“保存YOLO标注”；关闭后只显示“保存”，默认保存 Labelme 标注。"
    assert dialog.line_expand_label.text() == "直线标注 ⓘ"
    assert dialog.line_expand_label.toolTip() == "开启后可在标注类型中使用直线扩展；关闭后该绘制类型不会显示。"
    assert dialog.line_expand_pixels_label.text() == "直线扩展像素 ⓘ"
    assert dialog.line_expand_pixels_label.toolTip() == "设置直线扩展生成旋转矩形时，沿线段两侧扩展的像素宽度。"


def test_annotation_settings_dialog_hides_symbol_but_keeps_tooltip_when_disabled(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication
    from scr.ui.views.annotation import AnnotationPage
    from scr.ui.views.annotation_dialogs import AnnotationSettingsDialog

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    settings["features"]["show_help_icons"] = False
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )

    page = AnnotationPage(fake_app)
    dialog = AnnotationSettingsDialog(
        enabled=True,
        pixels=10,
        auto_save=True,
        auto_convert_yolo=False,
        show_yolo_save_in_context_menu=False,
        continuous_draw=False,
        quick_draw=True,
        yolo_dir=str(tmp_path / "labels"),
        parent=page,
    )

    assert dialog.continuous_draw_check.text() == "开启连续标注"
    assert dialog.continuous_draw_check.toolTip() == "开启后完成一个标注会继续保持当前绘制类型；关闭后每次完成标注都会自动回到选择模式。"
    assert dialog.show_yolo_context_check.text() == "右键显示保存YOLO标注"
    assert dialog.line_expand_label.text() == "直线标注"
    assert dialog.line_expand_label.toolTip() == "开启后可在标注类型中使用直线扩展；关闭后该绘制类型不会显示。"


def test_annotation_page_can_change_annotation_class_from_context_target(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication
    from scr.ui.views.annotation import AnnotationPage
    from scr.services.editable_annotation_service import EditableAnnotation

    images_dir = tmp_path / "images"
    images_dir.mkdir()
    from PIL import Image

    Image.new("RGB", (32, 32), "white").save(images_dir / "1.jpg")

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    settings["annotation"]["auto_save"] = False
    settings["dataset"]["class_names"] = ["weld", "scratch"]
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )

    page = AnnotationPage(fake_app)
    page.canvas.annotations = [
        EditableAnnotation(0, "rect", [(1, 1), (10, 1), (10, 10), (1, 10)])
    ]
    page.canvas.selected_index = 0
    page.refresh_annotation_list()

    page.set_selected_annotation_class(1)

    assert page.canvas.annotations[0].class_id == 1
    assert page.annotation_list.item(0).text().startswith("1.scratch-")


def test_annotation_page_annotation_list_context_delete_action_has_no_del_hint(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication, QLabel, QMenu
    from scr.ui.views.annotation import AnnotationPage
    from scr.services.editable_annotation_service import EditableAnnotation

    images_dir = tmp_path / "images"
    images_dir.mkdir()
    from PIL import Image

    Image.new("RGB", (32, 32), "white").save(images_dir / "1.jpg")

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    settings["dataset"]["class_names"] = ["weld", "scratch"]
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )

    page = AnnotationPage(fake_app)
    menu = QMenu(page)

    action = page._add_danger_menu_action(menu, "删除标注")
    widget = action.defaultWidget()
    labels = [label.text() for label in widget.findChildren(QLabel)]

    assert "删除标注" in labels
    assert "Del" not in labels


def test_annotation_canvas_delete_action_uses_native_shortcut():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.ui.qt import QApplication, QMenu, Qt
    from scr.ui.views.annotation_canvas import AnnotationCanvas

    app = QApplication.instance() or QApplication([])
    canvas = AnnotationCanvas()
    menu = QMenu(canvas)

    action = menu.addAction("删除")
    action.setShortcut(Qt.Key.Key_Delete)
    action.setShortcutVisibleInContextMenu(True)

    assert action.text() == "删除"
    assert action.shortcut().toString() == "Del"
    assert action.isShortcutVisibleInContextMenu() is True


def test_annotation_canvas_continuous_draw_keeps_shape_after_finish():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.ui.views.annotation_canvas import AnnotationCanvas

    canvas = AnnotationCanvas()
    canvas.set_interaction_config(True, False)
    canvas.set_draw_shape("rect")

    canvas._handle_two_click_shape_click((10.0, 10.0))
    canvas._handle_two_click_shape_click((30.0, 30.0))

    assert len(canvas.annotations) == 1
    assert canvas.draw_shape == "rect"
    assert canvas.drag_start is None
    assert canvas.drag_current is None


def test_annotation_canvas_line_expand_finishes_on_second_click_when_quick_draw_disabled():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.ui.views.annotation_canvas import AnnotationCanvas

    canvas = AnnotationCanvas()
    canvas.set_interaction_config(False, False)
    canvas.set_draw_shape("line_expand")
    canvas.set_line_expand_config(True, 12)

    canvas._handle_rotated_shape_click((10.0, 10.0))
    assert canvas.obb_first == (10.0, 10.0)

    canvas._handle_rotated_shape_click((30.0, 10.0))

    assert len(canvas.annotations) == 1
    assert canvas.annotations[0].shape == "line_expand"
    assert canvas.draw_shape == "select"
    assert canvas.obb_first is None
    assert canvas.obb_second is None


def test_annotation_canvas_line_expand_quick_draw_finishes_on_mouse_release():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtCore import QPointF
    from types import SimpleNamespace

    from scr.ui.qt import QPixmap, Qt
    from scr.ui.views.annotation_canvas import AnnotationCanvas

    canvas = AnnotationCanvas()
    canvas.set_interaction_config(False, True)
    canvas.set_draw_shape("line_expand")
    canvas.set_line_expand_config(True, 12)
    canvas.pixmap = QPixmap(100, 100)
    canvas.image_size = (100, 100)

    press_event = SimpleNamespace(
        button=lambda: Qt.MouseButton.LeftButton,
        position=lambda: QPointF(10.0, 10.0),
    )
    canvas._widget_to_image = lambda _point, clamp=False: (10.0, 10.0)
    canvas.mousePressEvent(press_event)

    assert canvas.drag_start == (10.0, 10.0)

    release_event = SimpleNamespace(
        button=lambda: Qt.MouseButton.LeftButton,
        position=lambda: QPointF(60.0, 10.0),
    )
    canvas._widget_to_image = lambda _point, clamp=False: (60.0, 10.0)
    canvas.mouseReleaseEvent(release_event)

    assert len(canvas.annotations) == 1
    assert canvas.annotations[0].shape == "line_expand"
    assert canvas.draw_shape == "select"
    assert canvas.drag_start is None
    assert canvas.drag_current is None


def test_annotation_canvas_polygon_clicking_existing_point_closes_and_flashes():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.ui.views.annotation_canvas import AnnotationCanvas

    canvas = AnnotationCanvas()
    canvas.set_draw_shape("polygon")

    canvas._handle_polygon_click((10.0, 10.0))
    canvas._handle_polygon_click((30.0, 10.0))
    canvas._handle_polygon_click((30.0, 30.0))
    canvas._handle_polygon_click((10.0, 10.0))

    assert len(canvas.annotations) == 1
    assert canvas.annotations[0].shape == "polygon"
    assert len(canvas.annotations[0].points) == 3
    assert canvas.flash_index == 0
    assert canvas.draw_shape == "select"
    assert canvas.polygon_points == []


def test_annotation_canvas_polygon_hover_on_closing_point_uses_pointing_hand_cursor():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.ui.qt import Qt
    from scr.ui.views.annotation_canvas import AnnotationCanvas

    canvas = AnnotationCanvas()
    canvas.set_draw_shape("polygon")
    canvas.polygon_points = [(10.0, 10.0), (30.0, 10.0), (30.0, 30.0)]

    canvas._update_polygon_hover_state((10.0, 10.0))

    assert canvas.hovered_polygon_close_index == 0
    assert canvas.cursor().shape() == Qt.CursorShape.PointingHandCursor


def test_ai_prelabel_dialog_supports_following_and_custom_ranges(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication
    from scr.ui.views.annotation import AiPrelabelDialog, AnnotationPage

    images_dir = tmp_path / "images"
    images_dir.mkdir()
    from PIL import Image

    Image.new("RGB", (32, 32), "white").save(images_dir / "1.jpg")
    Image.new("RGB", (32, 32), "white").save(images_dir / "2.jpg")
    Image.new("RGB", (32, 32), "white").save(images_dir / "3.jpg")

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )

    page = AnnotationPage(fake_app)
    page.change_current_index(1)
    dialog = AiPrelabelDialog(page)

    dialog.range_combo.setCurrentText("当前及以后图片")
    assert dialog.range_count_label.text() == "已选择 2 张图片"

    dialog.custom_selected_images = [page.image_items[0], page.image_items[2]]
    dialog.range_combo.setCurrentText("自定义图片")
    assert dialog.range_count_label.isHidden() is True
    assert dialog.range_list_btn.isHidden() is False
    assert dialog.range_list_btn.text() == "列表"


def test_custom_ai_image_selection_dialog_bulk_actions_work(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.ui.qt import QApplication, QEvent, Qt
    from scr.ui.views.annotation import CustomAiImageSelectionDialog
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QMouseEvent

    app = QApplication.instance() or QApplication([])
    image_items = [tmp_path / f"{index}.jpg" for index in range(1, 4)]
    dialog = CustomAiImageSelectionDialog(image_items, [image_items[0]])

    assert dialog.selected_image_paths() == [image_items[0]]
    assert dialog.selected_count_label.text() == "已选择 1 张图片"

    dialog.select_all_visible()
    assert dialog.selected_image_paths() == image_items
    assert dialog.selected_count_label.text() == "已选择 3 张图片"

    dialog.invert_visible_selection()
    assert dialog.selected_image_paths() == []

    dialog.select_all_visible()
    dialog.clear_visible_selection()
    assert dialog.selected_image_paths() == []


def test_custom_ai_image_selection_dialog_supports_drag_select(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.ui.qt import QApplication, QEvent, Qt
    from scr.ui.views.annotation import CustomAiImageSelectionDialog
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QMouseEvent

    app = QApplication.instance() or QApplication([])
    image_items = [tmp_path / f"{index}.jpg" for index in range(1, 5)]
    dialog = CustomAiImageSelectionDialog(image_items, [])
    dialog.show()
    app.processEvents()

    first_item = dialog.listing.item(0)
    third_item = dialog.listing.item(2)
    first_rect = dialog.listing.visualItemRect(first_item)
    third_rect = dialog.listing.visualItemRect(third_item)
    press_pos = first_rect.center()
    move_pos = third_rect.center()

    press_event = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        press_pos,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    move_event = QMouseEvent(
        QEvent.Type.MouseMove,
        move_pos,
        Qt.MouseButton.NoButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    release_event = QMouseEvent(
        QEvent.Type.MouseButtonRelease,
        move_pos,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )

    QApplication.sendEvent(dialog.listing.viewport(), press_event)
    QApplication.sendEvent(dialog.listing.viewport(), move_event)
    QApplication.sendEvent(dialog.listing.viewport(), release_event)

    assert dialog.selected_image_paths() == image_items[:3]
    assert dialog.selected_count_label.text() == "已选择 3 张图片"


def test_custom_ai_image_selection_dialog_auto_scrolls_near_bottom_edge(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.ui.qt import QApplication, QEvent, Qt
    from scr.ui.views.annotation import CustomAiImageSelectionDialog
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QMouseEvent

    app = QApplication.instance() or QApplication([])
    image_items = [tmp_path / f"{index:02d}.jpg" for index in range(1, 41)]
    dialog = CustomAiImageSelectionDialog(image_items, [])
    dialog.resize(320, 260)
    dialog.show()
    app.processEvents()

    first_item = dialog.listing.item(0)
    press_pos = dialog.listing.visualItemRect(first_item).center()
    edge_pos = QPoint(
        dialog.listing.viewport().width() // 2,
        dialog.listing.viewport().height() + 12,
    )

    press_event = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        press_pos,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    move_event = QMouseEvent(
        QEvent.Type.MouseMove,
        edge_pos,
        Qt.MouseButton.NoButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    release_event = QMouseEvent(
        QEvent.Type.MouseButtonRelease,
        edge_pos,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )

    scrollbar = dialog.listing.verticalScrollBar()
    start_value = scrollbar.value()

    QApplication.sendEvent(dialog.listing.viewport(), press_event)
    QApplication.sendEvent(dialog.listing.viewport(), move_event)
    assert dialog._auto_scroll_timer.isActive() is True
    dialog._perform_auto_scroll_step()
    dialog._perform_auto_scroll_step()
    QApplication.sendEvent(dialog.listing.viewport(), release_event)

    assert scrollbar.value() > start_value
    assert dialog._auto_scroll_timer.isActive() is False


def test_ai_prelabel_dialog_populates_mapping_from_project_classes(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication
    from scr.ui.views.annotation import AiPrelabelDialog, AnnotationPage

    images_dir = tmp_path / "images"
    images_dir.mkdir()
    from PIL import Image

    Image.new("RGB", (32, 32), "white").save(images_dir / "1.jpg")

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    settings["dataset"]["class_names"] = ["weld", "scratch"]
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )

    page = AnnotationPage(fake_app)
    dialog = AiPrelabelDialog(page)
    dialog.apply_model_labels(dialog.resolved_model_path(), ["weld", "person"])

    assert dialog.mapping_table.rowCount() == 2
    first_combo = dialog.mapping_table.cellWidget(0, 2)
    second_combo = dialog.mapping_table.cellWidget(1, 2)
    assert first_combo.currentText() == "weld"
    assert second_combo.currentText() == "-- 跳过 --"


def test_ai_prelabel_dialog_lists_trained_best_models_before_base_models(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication
    from scr.ui.views.annotation import AiPrelabelDialog, AnnotationPage

    images_dir = tmp_path / "images"
    images_dir.mkdir()
    from PIL import Image

    Image.new("RGB", (32, 32), "white").save(images_dir / "1.jpg")
    models_dir = tmp_path / "data" / "models"
    models_dir.mkdir(parents=True)
    (models_dir / "yolov8s.pt").write_text("base", encoding="utf-8")
    run_dir = tmp_path / "result" / "train-2" / "weights"
    run_dir.mkdir(parents=True)
    (run_dir / "best.pt").write_text("best", encoding="utf-8")
    (run_dir / "last.pt").write_text("last", encoding="utf-8")

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )

    page = AnnotationPage(fake_app)
    dialog = AiPrelabelDialog(page)
    items = [dialog.model_combo.itemText(i) for i in range(dialog.model_combo.count())]

    assert items[0] == "train-2\\best.pt"
    assert "yolov8s.pt" in items
    assert items.index("train-2\\best.pt") < items.index("yolov8s.pt")


def test_ai_prelabel_dialog_persists_preferences_on_close(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication
    from scr.ui.views.annotation import AiPrelabelDialog, AnnotationPage

    images_dir = tmp_path / "images"
    images_dir.mkdir()
    from PIL import Image

    Image.new("RGB", (32, 32), "white").save(images_dir / "1.jpg")
    Image.new("RGB", (32, 32), "white").save(images_dir / "2.jpg")
    model_path = tmp_path / "data" / "models" / "custom.pt"
    model_path.parent.mkdir(parents=True)
    model_path.write_text("model", encoding="utf-8")

    saved_settings = {}

    def save_settings(data):
        saved_settings.clear()
        saved_settings.update(data)

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=save_settings),
    )

    page = AnnotationPage(fake_app)
    first_dialog = AiPrelabelDialog(page)
    first_dialog.model_combo.setCurrentText(str(model_path))
    first_dialog.conf_spin.setValue(0.65)
    first_dialog.iou_spin.setValue(0.35)
    first_dialog.range_combo.setCurrentText("自定义图片")
    first_dialog.replace_radio.setChecked(True)
    first_dialog.custom_selected_images = [page.image_items[1]]
    first_dialog.accept()

    assert saved_settings["annotation"]["ai_prelabel"]["confidence"] == 0.65
    assert saved_settings["annotation"]["ai_prelabel"]["iou"] == 0.35
    assert saved_settings["annotation"]["ai_prelabel"]["range_mode"] == "自定义图片"
    assert saved_settings["annotation"]["ai_prelabel"]["process_mode"] == "替换"
    assert saved_settings["annotation"]["ai_prelabel"]["custom_selected_images"] == ["images\\2.jpg"]

    second_dialog = AiPrelabelDialog(page)
    assert second_dialog.conf_spin.value() == 0.65
    assert second_dialog.iou_spin.value() == 0.35
    assert second_dialog.current_range_mode() == "自定义图片"
    assert second_dialog.current_process_mode() == "替换"
    assert second_dialog.custom_selected_images == [page.image_items[1].resolve()]


def test_ai_prelabel_dialog_ignores_stale_model_label_results_after_switch(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication
    from scr.ui.views.annotation import AiPrelabelDialog, AnnotationPage

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

    page = AnnotationPage(fake_app)
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
