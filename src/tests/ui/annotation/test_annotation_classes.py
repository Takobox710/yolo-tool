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
    from src.ui.features.annotation import class_manager_dialog
    from src.ui.features.annotation.dialogs import ClassManagerDialog

    app = QApplication.instance() or QApplication([])
    manager = ClassManagerDialog(["weld", "scratch"], annotation_counts=[2, 0])
    calls = []

    class FakeConversionDialog:
        def __init__(self, class_names, annotation_counts, parent):
            calls.append((class_names, annotation_counts, parent))

        def exec(self):
            return QDialog.DialogCode.Rejected

    monkeypatch.setattr(
        class_manager_dialog,
        "ClassConversionDialog",
        FakeConversionDialog,
    )
    manager.convert_button.click()

    assert calls == [(["weld", "scratch"], [2, 0], manager)]




