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
    items = [page.file_list.item(i).text() for i in range(page.file_list.count())]

    assert items[0].startswith("☑︎ ")
    assert items[1].startswith("☐ ")


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
    dialog.apply_model_labels(["weld", "person"])

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
