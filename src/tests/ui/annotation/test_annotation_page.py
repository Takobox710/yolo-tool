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


def _show_annotation_page(page, app):
    page.on_show()
    app.processEvents()
    app.processEvents()
    return page


def test_annotation_page_uses_picture_list_header_and_count(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication, QLabel
    from src.ui.features.annotation.page import AnnotationPage

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

    page = _show_annotation_page(AnnotationPage(fake_app), app)
    labels = [label.text() for label in page.findChildren(QLabel)]

    assert "图片列表：" in labels
    assert page.file_count_label.text() == "1/2"


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


def test_annotation_page_delete_selected_updates_current_checkbox_without_full_refresh(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    import json

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AnnotationPage

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

    page = _show_annotation_page(AnnotationPage(fake_app), app)
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

    from src.ui.features.annotation.canvas.widget import AnnotationCanvas

    canvas = AnnotationCanvas()
    assert canvas._can_show_cancel_drawing_action() is False

    canvas.set_draw_shape("rect")
    assert canvas._can_show_cancel_drawing_action() is True

    canvas.set_draw_shape("select")
    assert canvas._can_show_cancel_drawing_action() is False

    canvas.drag_start = (10.0, 10.0)
    assert canvas._can_show_cancel_drawing_action() is True


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


def test_annotation_canvas_switching_from_edit_mode_clears_selection():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.annotation import EditableAnnotation
    from src.ui.features.annotation.canvas.widget import AnnotationCanvas

    canvas = AnnotationCanvas()
    canvas.annotations = [
        EditableAnnotation(0, "rect", [(1.0, 1.0), (10.0, 1.0), (10.0, 10.0), (1.0, 10.0)])
    ]
    canvas.selected_index = 0

    canvas.set_draw_shape("rect")

    assert canvas.selected_index == -1


def test_annotation_canvas_clicking_beside_annotation_clears_selection():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from types import SimpleNamespace

    from src.services.annotation import EditableAnnotation
    from src.shared.qt import Qt, QPixmap
    from src.ui.features.annotation.canvas.widget import AnnotationCanvas

    canvas = AnnotationCanvas()
    canvas.pixmap = QPixmap(100, 100)
    canvas.image_size = (100, 100)
    canvas.annotations = [
        EditableAnnotation(0, "rect", [(10.0, 10.0), (30.0, 10.0), (30.0, 30.0), (10.0, 30.0)])
    ]
    canvas.selected_index = 0
    canvas.hovered_index = 0
    canvas._widget_to_image = lambda _point, clamp=False: (80.0, 80.0)
    canvas._hit_handle = lambda _point: None
    canvas._hit_test = lambda _point: -1

    canvas.mousePressEvent(
        SimpleNamespace(
            button=lambda: Qt.MouseButton.LeftButton,
            position=lambda: None,
        )
    )

    assert canvas.selected_index == -1
    assert canvas.hovered_index == -1


def test_annotation_canvas_continuous_draw_clears_previous_selection_on_next_click():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from types import SimpleNamespace

    from src.services.annotation import EditableAnnotation
    from src.shared.qt import Qt, QPixmap
    from src.ui.features.annotation.canvas.widget import AnnotationCanvas

    canvas = AnnotationCanvas()
    canvas.pixmap = QPixmap(100, 100)
    canvas.image_size = (100, 100)
    canvas.set_interaction_config(True, False)
    canvas.set_draw_shape("rect")
    canvas.annotations = [
        EditableAnnotation(0, "rect", [(10.0, 10.0), (30.0, 10.0), (30.0, 30.0), (10.0, 30.0)])
    ]
    canvas.selected_index = 0
    canvas._widget_to_image = lambda _point, clamp=False: (70.0, 70.0)

    canvas.mousePressEvent(
        SimpleNamespace(
            button=lambda: Qt.MouseButton.LeftButton,
            position=lambda: None,
        )
    )

    assert canvas.selected_index == -1
    assert canvas.drag_start == (70.0, 70.0)


def test_annotation_canvas_delete_action_only_available_when_annotation_selected():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.annotation import EditableAnnotation
    from src.ui.features.annotation.canvas.widget import AnnotationCanvas

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

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AnnotationPage

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

    page = _show_annotation_page(AnnotationPage(fake_app), app)
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

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AnnotationPage

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

    page = _show_annotation_page(AnnotationPage(fake_app), app)
    assert page.canvas.can_save_default is True
    assert page.canvas.can_save_labelme is True
    assert page.canvas.can_save_yolo is False


def test_annotation_page_canvas_context_undo_flag_tracks_dirty_state(tmp_path):
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
    settings["annotation"]["auto_save"] = False
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )

    page = _show_annotation_page(AnnotationPage(fake_app), app)
    assert page.canvas.can_undo is False

    page.dirty = True
    page._refresh_manual_action_buttons()

    assert page.canvas.can_undo is True


def test_annotation_page_marks_current_image_unsaved_when_labelme_auto_save_disabled(tmp_path):
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
    settings["annotation"]["auto_save"] = False
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )

    page = _show_annotation_page(AnnotationPage(fake_app), app)
    widget = page.file_list.itemWidget(page.file_list.item(0))
    assert widget.isUnsaved() is False

    page.dirty = True
    page._update_current_file_list_item()

    assert widget.isUnsaved() is True


def test_annotation_page_context_delete_annotations_removes_label_files(tmp_path):
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
    settings["paths"]["labels_dir"] = str(labels_dir)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )

    page = _show_annotation_page(AnnotationPage(fake_app), app)
    page.clear_annotations_for_image(image_path)

    assert (images_dir / "1.json").exists() is False
    assert (labels_dir / "1.txt").exists() is False


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
    settings["paths"]["labels_dir"] = str(labels_dir)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )

    page = _show_annotation_page(AnnotationPage(fake_app), app)
    page.delete_image_and_annotations(image_path)

    assert image_path.exists() is False
    assert (images_dir / "1.json").exists() is False
    assert (labels_dir / "1.txt").exists() is False


def test_ai_prelabel_dialog_uses_expected_range_count(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AiPrelabelDialog, AnnotationPage

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

    page = _show_annotation_page(AnnotationPage(fake_app), app)
    dialog = AiPrelabelDialog(page)

    assert dialog.range_count_label.text() == "已选择 1 张图片"
    dialog.range_combo.setCurrentText("全部图片")
    assert dialog.range_count_label.text() == "已选择 2 张图片"


def test_annotation_canvas_two_click_rectangle_respects_quick_draw_setting():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.ui.features.annotation.canvas.widget import AnnotationCanvas

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

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AnnotationPage
    from src.ui.features.annotation.dialogs import AnnotationSettingsDialog

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )

    page = _show_annotation_page(AnnotationPage(fake_app), app)
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
    assert dialog.show_annotation_names_check.text() == "显示标注名称"
    assert dialog.show_annotation_names_check.isChecked() is False
    assert dialog.line_expand_label.text() == "直线标注 ⓘ"
    assert dialog.line_expand_label.toolTip() == "开启后可在标注类型中使用直线扩展；关闭后该绘制类型不会显示。"
    assert dialog.line_expand_pixels_label.text() == "直线扩展像素 ⓘ"
    assert dialog.line_expand_pixels_label.toolTip() == "设置直线扩展生成旋转矩形时，沿线段两侧扩展的像素宽度。"


def test_annotation_canvas_name_visibility_is_configurable_in_rendering(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QColor, QPaintEvent

    from src.services.annotation import EditableAnnotation
    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication, QPixmap, Qt
    from src.ui.features.annotation.page import AnnotationPage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )
    page = AnnotationPage(fake_app)
    page._refresh_class_state()

    assert settings["annotation"]["show_annotation_names"] is False
    assert page.canvas.show_annotation_names is False

    calls = []
    page.canvas.pixmap = QPixmap(32, 32)
    page.canvas.image_size = (32, 32)
    page.canvas.annotations = [
        EditableAnnotation(0, "rect", [(2.0, 2.0), (20.0, 2.0), (20.0, 20.0), (2.0, 20.0)])
    ]
    page.canvas._draw_annotation = lambda painter, annotation, **kwargs: calls.append(kwargs)
    page.canvas.paintEvent(QPaintEvent(page.canvas.rect()))
    assert calls[0]["show_label"] is False

    settings["annotation"]["show_annotation_names"] = True
    page._refresh_class_state()
    assert page.canvas.show_annotation_names is True
    page.canvas.paintEvent(QPaintEvent(page.canvas.rect()))

    assert calls[1]["show_label"] is True


def test_annotation_canvas_drawing_preview_uses_green_and_only_polygon_has_light_green_fill():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QColor, QImage, QPainter, QPaintEvent

    from src.services.annotation import EditableAnnotation
    from src.shared.qt import QApplication, QPixmap
    from src.ui.features.annotation.canvas.render import PREVIEW_COLOR, PREVIEW_FILL_COLOR
    from src.ui.features.annotation.canvas.widget import AnnotationCanvas

    app = QApplication.instance() or QApplication([])
    canvas = AnnotationCanvas()
    canvas.pixmap = QPixmap(32, 32)
    canvas.pixmap.fill(QColor("#FFFFFF"))
    canvas.image_size = (32, 32)
    canvas.set_draw_shape("rect")
    canvas.drag_start = (2.0, 2.0)
    canvas.drag_current = (20.0, 20.0)
    canvas._image_to_widget = lambda point: QPointF(*point)
    image = QImage(32, 32, QImage.Format.Format_RGB32)
    image.fill(QColor("#FFFFFF"))
    painter = QPainter(image)
    rectangle = EditableAnnotation(0, "rect", [(2.0, 2.0), (20.0, 2.0), (20.0, 20.0), (2.0, 20.0)])
    canvas._draw_annotation(
        painter,
        rectangle,
        selected=True,
        show_label=False,
    )
    painter.end()
    selected_rectangle_color = image.pixelColor(10, 10)

    assert selected_rectangle_color.red() == 255
    assert selected_rectangle_color.green() < 230
    assert selected_rectangle_color.blue() < 230

    image.fill(QColor("#FFFFFF"))
    painter = QPainter(image)
    canvas._draw_annotation(painter, rectangle, preview=True, show_label=False)
    painter.end()
    rectangle_outline_color = image.pixelColor(2, 10)

    assert rectangle_outline_color == QColor(127, 255, 127)
    assert PREVIEW_COLOR == QColor(0, 255, 0, 128)

    image.fill(QColor("#FFFFFF"))
    painter = QPainter(image)
    canvas._draw_preview_polyline(
        painter,
        [(2.0, 2.0), (20.0, 2.0), (20.0, 20.0)],
        closed=False,
        fill=True,
    )
    painter.end()
    polygon_fill_color = image.pixelColor(12, 10)

    assert polygon_fill_color == QColor(191, 255, 191)
    assert PREVIEW_FILL_COLOR == QColor(0, 255, 0, 64)

    calls = []
    canvas._draw_annotation = lambda painter, annotation, **kwargs: calls.append(kwargs)

    canvas.paintEvent(QPaintEvent(canvas.rect()))

    assert calls == [{"preview": True, "selected": True, "show_label": False}]

    polygon_calls = []
    canvas.set_draw_shape("polygon")
    canvas.drag_start = None
    canvas.drag_current = None
    canvas.polygon_points = [(2.0, 2.0), (20.0, 2.0), (20.0, 20.0)]
    canvas.preview_line_end = None
    canvas._draw_preview_polyline = lambda painter, points, **kwargs: polygon_calls.append(kwargs)
    canvas.paintEvent(QPaintEvent(canvas.rect()))

    assert polygon_calls == [{"closed": False, "handle_points": canvas.polygon_points, "fill": True}]


def test_annotation_canvas_handle_diameter_is_nine_pixels():
    from src.ui.features.annotation.canvas.hit_test import HANDLE_RADIUS

    assert HANDLE_RADIUS == 4.5
    assert HANDLE_RADIUS * 2 == 9


def test_annotation_canvas_handle_shapes_distinguish_preview_hover_and_selection():
    from PySide6.QtCore import QPointF

    from src.services.annotation import EditableAnnotation
    from src.shared.qt import QApplication
    from src.ui.features.annotation.canvas.widget import AnnotationCanvas

    app = QApplication.instance() or QApplication([])
    canvas = AnnotationCanvas()
    canvas.selected_index = 0
    canvas._image_to_widget = lambda point: QPointF(*point)
    annotation = EditableAnnotation(
        0,
        "rect",
        [(4.0, 4.0), (28.0, 4.0), (28.0, 28.0), (4.0, 28.0)],
    )

    class Painter:
        def __init__(self):
            self.shapes = []

        def setPen(self, _pen):
            pass

        def setBrush(self, _brush):
            pass

        def drawRect(self, _rect):
            self.shapes.append("rect")

        def drawEllipse(self, _ellipse):
            self.shapes.append("ellipse")

    canvas.hovered_index = 0
    hovered_painter = Painter()
    canvas._draw_handles(hovered_painter, annotation, hovered_handle=("point", 1))
    assert hovered_painter.shapes == ["ellipse", "rect", "ellipse", "ellipse"]

    selected_painter = Painter()
    canvas._draw_handles(selected_painter, annotation)
    assert selected_painter.shapes == ["ellipse"] * 4

    preview_painter = Painter()
    canvas._draw_handles(preview_painter, annotation, preview=True)
    assert preview_painter.shapes == ["ellipse"] * 4


def test_annotation_canvas_hovered_point_is_the_only_square_and_starts_direct_edit():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from types import SimpleNamespace

    from PySide6.QtCore import QPointF

    from src.services.annotation import EditableAnnotation
    from src.shared.qt import QApplication, QPixmap, Qt
    from src.ui.features.annotation.canvas.widget import AnnotationCanvas

    app = QApplication.instance() or QApplication([])
    canvas = AnnotationCanvas()
    canvas.pixmap = QPixmap(64, 64)
    canvas.image_size = (64, 64)
    canvas.annotations = [
        EditableAnnotation(
            0,
            "rect",
            [(10.0, 10.0), (30.0, 10.0), (30.0, 30.0), (10.0, 30.0)],
        )
    ]
    canvas._widget_to_image = lambda point, clamp=False: (point.x(), point.y())
    canvas._update_hover_state((10.0, 10.0))

    assert canvas.hovered_index == 0
    assert canvas.hovered_handle == ("point", 0)

    canvas.mousePressEvent(
        SimpleNamespace(
            button=lambda: Qt.MouseButton.LeftButton,
            position=lambda: QPointF(10.0, 10.0),
        )
    )

    assert canvas.selected_index == 0
    assert canvas.active_handle == ("point", 0)
    del app


def test_annotation_canvas_unselected_edit_annotations_show_points_without_fill():
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QColor, QImage, QPainter

    from src.services.annotation import EditableAnnotation
    from src.shared.qt import QApplication
    from src.ui.features.annotation.canvas.widget import AnnotationCanvas

    app = QApplication.instance() or QApplication([])
    canvas = AnnotationCanvas()
    canvas.draw_shape = "select"
    canvas._image_to_widget = lambda point: QPointF(*point)
    annotation = EditableAnnotation(
        0,
        "rect",
        [(4.0, 4.0), (28.0, 4.0), (28.0, 28.0), (4.0, 28.0)],
    )
    image = QImage(32, 32, QImage.Format.Format_RGB32)
    image.fill(QColor("#FFFFFF"))
    painter = QPainter(image)
    canvas._draw_annotation(painter, annotation, hovered=False, selected=False, show_label=False)
    painter.end()

    assert image.pixelColor(16, 16) == QColor("#FFFFFF")

    handle_calls = []
    canvas._draw_handles = lambda painter, annotation, **kwargs: handle_calls.append(kwargs)
    canvas.draw_shape = "rect"
    image.fill(QColor("#FFFFFF"))
    painter = QPainter(image)
    canvas._draw_annotation(painter, annotation, hovered=True, selected=False, show_label=False)
    painter.end()

    assert handle_calls == [{"preview": False, "hovered_handle": None}]

    image.fill(QColor("#FFFFFF"))
    painter = QPainter(image)
    canvas._draw_annotation(painter, annotation, hovered=True, selected=False, show_label=False)
    painter.end()

    hovered_color = image.pixelColor(16, 16)
    assert hovered_color != QColor("#FFFFFF")
    assert hovered_color.red() > hovered_color.green()
    assert hovered_color == QColor(255, 185, 185)


def test_annotation_settings_dialog_hides_symbol_but_keeps_tooltip_when_disabled(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AnnotationPage
    from src.ui.features.annotation.dialogs import AnnotationSettingsDialog

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    settings["features"]["show_help_icons"] = False
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )

    page = _show_annotation_page(AnnotationPage(fake_app), app)
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

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AnnotationPage
    from src.services.annotation import EditableAnnotation

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

    page = _show_annotation_page(AnnotationPage(fake_app), app)
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

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication, QLabel, QMenu
    from src.ui.features.annotation.page import AnnotationPage
    from src.services.annotation import EditableAnnotation

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

    page = _show_annotation_page(AnnotationPage(fake_app), app)
    menu = QMenu(page)

    action = page._add_danger_menu_action(menu, "删除标注")
    widget = action.defaultWidget()
    labels = [label.text() for label in widget.findChildren(QLabel)]

    assert "删除标注" in labels
    assert "Del" not in labels


def test_annotation_canvas_delete_action_uses_native_shortcut():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.shared.qt import QApplication, QMenu, Qt
    from src.ui.features.annotation.canvas.widget import AnnotationCanvas

    app = QApplication.instance() or QApplication([])
    canvas = AnnotationCanvas()
    menu = QMenu(canvas)

    action = menu.addAction("删除")
    action.setShortcut(Qt.Key.Key_Delete)
    action.setShortcutVisibleInContextMenu(True)

    assert action.text() == "删除"
    assert action.shortcut().toString() == "Del"
    assert action.isShortcutVisibleInContextMenu() is True


def test_draw_shape_dialog_shows_edit_option_above_divider():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.shared.qt import QApplication, QFrame, QPushButton
    from src.ui.features.annotation.dialogs import DrawShapeDialog

    app = QApplication.instance() or QApplication([])
    dialog = DrawShapeDialog(line_expand_enabled=True)
    buttons = [button.text() for button in dialog.findChildren(QPushButton)]

    assert buttons[0] == "编辑"
    assert buttons[1:] == ["矩形框", "有向矩形", "镜像有向矩形", "多边形", "圆形", "直线扩展"]
    assert dialog.findChild(QFrame, "drawShapeDivider") is not None


def test_draw_shape_dialog_edit_option_returns_select_mode():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.shared.qt import QApplication, QPushButton
    from src.ui.features.annotation.dialogs import DrawShapeDialog

    app = QApplication.instance() or QApplication([])
    dialog = DrawShapeDialog(line_expand_enabled=False)
    edit_button = next(
        button for button in dialog.findChildren(QPushButton) if button.text() == "编辑"
    )

    edit_button.click()

    assert dialog.selected_shape == "select"
    assert dialog.result() == dialog.DialogCode.Accepted


def test_annotation_canvas_continuous_draw_keeps_shape_after_finish():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.ui.features.annotation.canvas.widget import AnnotationCanvas

    canvas = AnnotationCanvas()
    canvas.set_interaction_config(True, False)
    canvas.set_draw_shape("rect")

    canvas._handle_two_click_shape_click((10.0, 10.0))
    canvas._handle_two_click_shape_click((30.0, 30.0))

    assert len(canvas.annotations) == 1
    assert canvas.draw_shape == "rect"
    assert canvas.selected_index == -1
    assert canvas.drag_start is None
    assert canvas.drag_current is None


def test_annotation_canvas_two_click_rectangle_refreshes_after_second_click():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from types import SimpleNamespace

    from PySide6.QtCore import QPointF

    from src.shared.qt import QApplication, QPixmap, Qt
    from src.ui.features.annotation.canvas.widget import AnnotationCanvas

    app = QApplication.instance() or QApplication([])
    canvas = AnnotationCanvas()
    canvas.set_interaction_config(False, False)
    canvas.set_draw_shape("rect")
    canvas.pixmap = QPixmap(100, 100)
    canvas.image_size = (100, 100)
    canvas._widget_to_image = lambda point, clamp=False: (point.x(), point.y())
    updates = []
    canvas.update = lambda: updates.append(True)

    def click(x, y):
        canvas.mousePressEvent(
            SimpleNamespace(
                button=lambda: Qt.MouseButton.LeftButton,
                position=lambda: QPointF(x, y),
            )
        )

    click(10.0, 10.0)
    first_click_updates = len(updates)
    click(30.0, 30.0)

    assert len(canvas.annotations) == 1
    assert canvas.draw_shape == "select"
    assert canvas.drag_start is None
    assert len(updates) > first_click_updates
    del app


def test_annotation_canvas_line_expand_finishes_on_second_click_when_quick_draw_disabled():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.ui.features.annotation.canvas.widget import AnnotationCanvas

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

    from src.shared.qt import QPixmap, Qt
    from src.ui.features.annotation.canvas.widget import AnnotationCanvas

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

    from src.ui.features.annotation.canvas.widget import AnnotationCanvas

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

    from src.shared.qt import Qt
    from src.ui.features.annotation.canvas.widget import AnnotationCanvas

    canvas = AnnotationCanvas()
    canvas.set_draw_shape("polygon")
    canvas.polygon_points = [(10.0, 10.0), (30.0, 10.0), (30.0, 30.0)]

    canvas._update_polygon_hover_state((10.0, 10.0))

    assert canvas.hovered_polygon_close_index == 0
    assert canvas.cursor().shape() == Qt.CursorShape.PointingHandCursor


def test_annotation_canvas_drawing_mode_uses_crosshair_cursor():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.shared.qt import Qt
    from src.ui.features.annotation.canvas.widget import AnnotationCanvas

    canvas = AnnotationCanvas()
    canvas.set_draw_shape("rect")

    canvas._update_hover_cursor()

    assert canvas.cursor().shape() == Qt.CursorShape.CrossCursor


def test_annotation_canvas_rectangle_mode_draws_full_crosshair_overlay():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from types import SimpleNamespace

    from PySide6.QtCore import QEvent, QPointF
    from PySide6.QtGui import QColor, QEnterEvent, QImage, QPainter, QPaintEvent

    from src.shared.qt import QApplication, QPixmap, Qt
    from src.ui.features.annotation.canvas.widget import AnnotationCanvas

    app = QApplication.instance() or QApplication([])
    canvas = AnnotationCanvas()
    canvas.setMinimumSize(0, 0)
    canvas.resize(100, 100)
    canvas.pixmap = QPixmap(100, 100)
    canvas.pixmap.fill(QColor("#FFFFFF"))
    canvas.image_size = (100, 100)
    canvas.set_draw_shape("rect")
    canvas._widget_to_image = lambda point, clamp=False: (point.x(), point.y())
    canvas.mouseMoveEvent(
        SimpleNamespace(position=lambda: QPointF(25, 40))
    )

    canvas.leaveEvent(QEvent(QEvent.Type.Leave))
    assert canvas.crosshair_position is None
    canvas.enterEvent(
        QEnterEvent(
            QPointF(25, 40),
            QPointF(25, 40),
            QPointF(25, 40),
        )
    )
    assert canvas.crosshair_position == (25.0, 40.0)
    assert canvas.cursor().shape() == Qt.CursorShape.CrossCursor

    lines = []

    class Painter:
        def setPen(self, pen):
            self.pen = pen

        def drawLine(self, start, end):
            lines.append((start, end))

    painter = Painter()
    canvas._draw_rect_crosshair(painter)
    assert painter.pen.color().name() == "#000000"
    assert painter.pen.style() == Qt.PenStyle.SolidLine
    assert [
        ((line[0].x(), line[0].y()), (line[1].x(), line[1].y()))
        for line in lines
    ] == [
        ((0.0, 40.0), (15.0, 40.0)),
        ((35.0, 40.0), (float(canvas.width()), 40.0)),
        ((25.0, 0.0), (25.0, 30.0)),
        ((25.0, 50.0), (25.0, float(canvas.height()))),
    ]

    image = QImage(100, 100, QImage.Format.Format_RGB32)
    image.fill(QColor("#FFFFFF"))
    image_painter = QPainter(image)
    canvas._draw_rect_crosshair(image_painter)
    image_painter.end()
    assert image.pixelColor(5, 40) == QColor("#000000")

    canvas.pixmap.fill(QColor("#000000"))
    image.fill(QColor("#000000"))
    image_painter = QPainter(image)
    canvas._draw_rect_crosshair(image_painter)
    image_painter.end()
    assert image.pixelColor(5, 40) == QColor("#484848")

    calls = []
    canvas._draw_rect_crosshair = lambda painter: calls.append(canvas.crosshair_position)

    canvas.paintEvent(QPaintEvent(canvas.rect()))

    assert calls == [(25.0, 40.0)]

    canvas.set_draw_shape("circle")
    canvas.paintEvent(QPaintEvent(canvas.rect()))

    assert calls == [(25.0, 40.0)]
    del app


def test_annotation_canvas_edit_mode_does_not_use_crosshair_for_selected_annotation():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.annotation import EditableAnnotation
    from src.shared.qt import Qt
    from src.ui.features.annotation.canvas.widget import AnnotationCanvas

    canvas = AnnotationCanvas()
    canvas.annotations = [
        EditableAnnotation(0, "rect", [(10.0, 10.0), (30.0, 10.0), (30.0, 30.0), (10.0, 30.0)])
    ]
    canvas.selected_index = 0
    canvas.hovered_index = -1

    canvas._update_hover_cursor()

    assert canvas.cursor().shape() == Qt.CursorShape.ArrowCursor


def test_ai_prelabel_dialog_supports_following_and_custom_ranges(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AiPrelabelDialog, AnnotationPage

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

    page = _show_annotation_page(AnnotationPage(fake_app), app)
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

    from src.shared.qt import QApplication, QEvent, Qt
    from src.ui.features.annotation.page import CustomAiImageSelectionDialog
    from PySide6.QtCore import QPoint, QPointF
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

    from src.shared.qt import QApplication, QEvent, Qt
    from src.ui.features.annotation.page import CustomAiImageSelectionDialog
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

    press_event = _mouse_event(
        dialog.listing.viewport(),
        QEvent.Type.MouseButtonPress,
        press_pos,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
    )
    move_event = _mouse_event(
        dialog.listing.viewport(),
        QEvent.Type.MouseMove,
        move_pos,
        Qt.MouseButton.NoButton,
        Qt.MouseButton.LeftButton,
    )
    release_event = _mouse_event(
        dialog.listing.viewport(),
        QEvent.Type.MouseButtonRelease,
        move_pos,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
    )

    QApplication.sendEvent(dialog.listing.viewport(), press_event)
    QApplication.sendEvent(dialog.listing.viewport(), move_event)
    QApplication.sendEvent(dialog.listing.viewport(), release_event)

    assert dialog.selected_image_paths() == image_items[:3]
    assert dialog.selected_count_label.text() == "已选择 3 张图片"


def test_custom_ai_image_selection_dialog_auto_scrolls_near_bottom_edge(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.shared.qt import QApplication, QEvent, Qt
    from src.ui.features.annotation.page import CustomAiImageSelectionDialog
    from PySide6.QtCore import QPoint, QPointF
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

    press_event = _mouse_event(
        dialog.listing.viewport(),
        QEvent.Type.MouseButtonPress,
        press_pos,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
    )
    move_event = _mouse_event(
        dialog.listing.viewport(),
        QEvent.Type.MouseMove,
        edge_pos,
        Qt.MouseButton.NoButton,
        Qt.MouseButton.LeftButton,
    )
    release_event = _mouse_event(
        dialog.listing.viewport(),
        QEvent.Type.MouseButtonRelease,
        edge_pos,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
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


def test_ai_prelabel_dialog_populates_mapping_from_project_classes(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AiPrelabelDialog, AnnotationPage

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

    page = _show_annotation_page(AnnotationPage(fake_app), app)
    dialog = AiPrelabelDialog(page)
    dialog.apply_model_labels(dialog.resolved_model_path(), ["weld", "person"])

    assert dialog.mapping_table.rowCount() == 2
    first_combo = dialog.mapping_table.cellWidget(0, 2)
    second_combo = dialog.mapping_table.cellWidget(1, 2)
    assert first_combo.currentText() == "weld"
    assert second_combo.currentText() == "-- 跳过 --"


def test_ai_prelabel_dialog_lists_trained_best_models_before_base_models(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AiPrelabelDialog, AnnotationPage

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

    page = _show_annotation_page(AnnotationPage(fake_app), app)
    dialog = AiPrelabelDialog(page)
    items = [dialog.model_combo.itemText(i) for i in range(dialog.model_combo.count())]

    assert items[0] == "train-2\\best.pt"
    assert "yolov8s.pt" in items
    assert items.index("train-2\\best.pt") < items.index("yolov8s.pt")


def test_ai_prelabel_dialog_persists_preferences_on_close(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AiPrelabelDialog, AnnotationPage

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

    page = _show_annotation_page(AnnotationPage(fake_app), app)
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


