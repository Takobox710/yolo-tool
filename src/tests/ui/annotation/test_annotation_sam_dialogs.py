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
    assert dialog.sam_advanced_button.size().width() == 50
    assert dialog.sam_advanced_button.size().height() == 36
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




def test_draw_shape_dialog_uses_compact_default_width():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.shared.qt import QApplication
    from src.ui.features.annotation.dialogs import DrawShapeDialog

    app = QApplication.instance() or QApplication([])
    dialog = DrawShapeDialog(False)
    dialog.show()
    app.processEvents()

    assert dialog.width() == 240
    assert dialog.layout().contentsMargins().top() == 12
    sam_widget = dialog.layout().itemAt(0).widget()
    assert sam_widget.layout().itemAt(0).geometry().top() == 0




def test_draw_shape_dialog_lists_sam3_and_preserves_custom_model_name(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.annotation.sam_assist import sam_model_spec_from_path
    from src.shared.qt import QApplication
    from src.ui.features.annotation.dialogs import DrawShapeDialog

    app = QApplication.instance() or QApplication([])
    sam3 = sam_model_spec_from_path(tmp_path / "sam3.pt")
    custom = sam_model_spec_from_path(tmp_path / "SAM_weld_custom.pt")
    dialog = DrawShapeDialog(False, sam_models=[sam3, custom])

    assert [dialog.sam_model_combo.itemText(i) for i in range(dialog.sam_model_combo.count())] == [
        "SAM 3",
        "SAM_weld_custom.pt",
    ]
    dialog.sam_model_combo.setCurrentIndex(1)
    assert dialog.sam_switch.isEnabled() is False
    assert dialog.sam_advanced_button.isEnabled() is False




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




def test_sam_advanced_settings_dialog_restores_values_and_defaults(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.annotation.sam_assist import sam_model_spec_from_path
    from src.shared.qt import QApplication
    from src.ui.features.annotation.sam import settings_dialog as sam_settings_dialog
    from src.ui.features.annotation.sam.settings_dialog import SamAdvancedSettingsDialog

    app = QApplication.instance() or QApplication([])
    model = sam_model_spec_from_path(tmp_path / "sam3.pt")
    dialog = SamAdvancedSettingsDialog(
        {
            "multimask_output": True,
            "minimum_score": 0.65,
            "minimum_area": 120,
            "polygon_simplification_ratio": 0.015,
        },
        "SAM 3",
        sam_models=[model],
        selected_model_key=model.key,
    )

    assert dialog.model_combo.currentText() == "SAM 3"
    assert dialog.selected_model_key() == model.key
    assert dialog.area_spin.width() == 102
    assert dialog.area_slider.maximum() == 1000
    dialog.area_slider.setValue(1000)
    assert dialog.area_spin.value() == 100_000_000
    dialog.area_spin.setValue(1)
    assert dialog.area_slider.value() == 0
    dialog.area_spin.setValue(120)
    from src.shared.qt import QAbstractSpinBox
    assert dialog.score_spin.buttonSymbols() == QAbstractSpinBox.ButtonSymbols.NoButtons
    assert dialog.area_spin.buttonSymbols() == QAbstractSpinBox.ButtonSymbols.NoButtons
    assert dialog.simplify_spin.buttonSymbols() == QAbstractSpinBox.ButtonSymbols.NoButtons
    opened = []
    monkeypatch.setattr(
        sam_settings_dialog.QDesktopServices,
        "openUrl",
        staticmethod(lambda url: opened.append(url.toLocalFile()) or True),
    )
    dialog.open_model_folder_button.click()
    assert [Path(path) for path in opened] == [tmp_path.resolve()]
    assert dialog.values() == {
        "multimask_output": True,
        "minimum_score": 0.65,
        "minimum_area": 120,
        "polygon_simplification_ratio": 0.015,
    }
    assert dialog.simplify_slider.maximum() == 30
    assert dialog.simplify_spin.maximum() == 1.5

    dialog.set_values({"polygon_simplification_ratio": 0.1})
    assert dialog.values()["polygon_simplification_ratio"] == 0.015

    dialog.reset_button.click()

    assert dialog.values() == {
        "multimask_output": False,
        "minimum_score": 0.0,
        "minimum_area": 4,
        "polygon_simplification_ratio": 0.002,
    }




def test_draw_shape_dialog_applies_advanced_sam_settings(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.annotation.sam_assist import sam_model_spec_from_path
    from src.shared.qt import QApplication, QDialog
    from src.ui.features.annotation import draw_shape_dialog
    from src.ui.features.annotation.dialogs import DrawShapeDialog

    app = QApplication.instance() or QApplication([])
    spec = sam_model_spec_from_path(tmp_path / "sam3.pt")
    applied = []

    class FakeAdvancedDialog:
        def __init__(self, values, model_name, parent, **kwargs):
            assert values["minimum_area"] == 4
            assert model_name == "SAM 3"
            assert parent is dialog

        def selected_model_key(self):
            return ""

        def exec(self):
            return QDialog.DialogCode.Accepted

        def values(self):
            return {
                "multimask_output": True,
                "minimum_score": 0.6,
                "minimum_area": 20,
                "polygon_simplification_ratio": 0.01,
            }

    monkeypatch.setattr(
        draw_shape_dialog,
        "SamAdvancedSettingsDialog",
        FakeAdvancedDialog,
    )
    dialog = DrawShapeDialog(
        False,
        sam_models=[spec],
        sam_settings={"minimum_area": 4},
        sam_settings_callback=lambda values: applied.append(values) or values,
    )

    dialog.sam_advanced_button.click()

    assert applied == [dialog.sam_settings]
    assert dialog.sam_settings["multimask_output"] is True




def test_sam_controller_applies_parameters_without_reloading_model(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.annotation import EditableAnnotation
    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AnnotationPage

    app = QApplication.instance() or QApplication([])
    saves = []
    fake_app = SimpleNamespace(
        settings=build_default_settings(tmp_path),
        settings_service=SimpleNamespace(save=lambda data: saves.append(data)),
    )
    page = AnnotationPage(fake_app)
    controller = page.sam_assist
    worker = object()
    controller._worker = worker
    controller._model_loaded = True
    controller._image_ready = True
    page.canvas.sam_preview_annotation = EditableAnnotation(
        0,
        "rect",
        [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)],
    )

    result = controller.apply_parameters(
        {
            "multimask_output": True,
            "minimum_score": 0.7,
            "minimum_area": 30,
            "polygon_simplification_ratio": 0.1,
        }
    )

    assert result["minimum_score"] == 0.7
    assert result["polygon_simplification_ratio"] == 0.015
    assert controller._worker is worker
    assert controller._model_loaded is True
    assert controller._image_ready is True
    assert page.canvas.sam_preview_annotation is None
    assert saves




