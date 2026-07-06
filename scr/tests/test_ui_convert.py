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


def test_class_mapping_dialog_disables_double_click_edit(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.ui.dialogs import ClassMappingDialog
    from scr.ui.qt import QApplication, QAbstractItemView

    app = QApplication.instance() or QApplication([])
    dialog = ClassMappingDialog(["a", "b"], {"a": "a", "b": "b"})
    triggers = dialog.table.editTriggers()

    assert not bool(triggers & QAbstractItemView.EditTrigger.DoubleClicked)
    assert bool(triggers & QAbstractItemView.EditTrigger.SelectedClicked)


def test_class_mapping_dialog_clears_current_cell_on_blank_click(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.ui.dialogs import ClassMappingDialog
    from scr.ui.qt import QApplication

    app = QApplication.instance() or QApplication([])
    dialog = ClassMappingDialog(["a"], {"a": "a"})
    dialog.table.setCurrentCell(0, 0)
    dialog.table.clearSelection()
    dialog.table.setCurrentIndex(dialog.table.model().index(-1, -1))

    assert dialog.table.currentRow() == -1


def test_convert_page_keeps_yolo_path_editable_when_labelme_mode_changes(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from scr.services.settings_service import build_default_settings
    from scr.ui.qt import QApplication
    from scr.ui.views.convert import ConvertTab

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        refresh_help_icon_visibility=lambda: None,
    )

    page = ConvertTab(fake_app)

    assert page.yolo_labels_box.isEnabled() is True
    assert page.yolo_labels_edit.isEnabled() is True
    assert page.line_edit.isEnabled() is False

    page.labelme_check.setChecked(False)

    assert page.yolo_labels_box.isEnabled() is True
    assert page.yolo_labels_edit.isEnabled() is True
    assert page.line_edit.isEnabled() is False
