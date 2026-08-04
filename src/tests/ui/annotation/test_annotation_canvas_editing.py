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

from src.tests.helpers.ui_source import read_app as _read_app, read_ui_bundle as _read_ui_bundle, show_page as _show_annotation_page

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
