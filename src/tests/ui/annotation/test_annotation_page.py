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
    settings["dataset"]["class_names"] = ["weld", "scratch"]
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
        def __init__(self, line_expand_enabled, parent):
            calls.append((line_expand_enabled, parent))

        def exec(self):
            return QDialog.DialogCode.Rejected

    monkeypatch.setattr(settings_actions, "DrawShapeDialog", FakeDrawShapeDialog)
    page = AnnotationPage(fake_app)

    page._draw_shortcut.activated.emit()

    assert page._draw_shortcut.key().toString() == "W"
    assert page._draw_shortcut.context() == Qt.ShortcutContext.WidgetWithChildrenShortcut
    assert calls == [(False, page)]


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

    assert settings["dataset"]["class_names"] == ["weld", "scratch"]


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
