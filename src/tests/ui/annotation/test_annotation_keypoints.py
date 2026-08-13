from __future__ import annotations

import os


def test_keypoint_setting_exposes_point_shape_without_hiding_existing_points():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.shared.qt import QApplication
    from src.ui.features.annotation.annotation_settings_dialog import AnnotationSettingsDialog
    from src.ui.features.annotation.draw_shape_dialog import DrawShapeDialog

    app = QApplication.instance() or QApplication([])
    settings_dialog = AnnotationSettingsDialog(
        False, 10, True, False, False, False, False, "labels", keypoint_enabled=True
    )
    draw_dialog = DrawShapeDialog(False, keypoint_enabled=True)

    assert settings_dialog.keypoint_check.isChecked() is True
    assert settings_dialog.values()[-2] is True
    assert ("点", "point") in draw_dialog._options


def test_annotation_list_warns_about_uncontained_keypoints(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from types import SimpleNamespace

    from src.services.annotation import EditableAnnotation
    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication, Qt
    from src.ui.features.annotation.annotation_list_delegate import KEYPOINT_WARNING
    from src.ui.features.annotation.page import AnnotationPage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    settings.dataset.class_names = ["weld"]
    settings.annotation.keypoint_enabled = True
    page = AnnotationPage(
        SimpleNamespace(settings=settings, settings_service=SimpleNamespace(save=lambda _data: None))
    )
    page.canvas.annotations = [
        EditableAnnotation(0, "rect", [(0, 0), (10, 0), (10, 10), (0, 10)]),
        EditableAnnotation(0, "point", [(5, 5)]),
        EditableAnnotation(0, "point", [(20, 20)]),
    ]
    page.refresh_annotation_list()

    assert KEYPOINT_WARNING not in page.annotation_list.item(1).text()
    assert page.annotation_list.item(2).text().endswith(KEYPOINT_WARNING)
    assert page.annotation_list.item(2).data(Qt.ItemDataRole.UserRole) is True
