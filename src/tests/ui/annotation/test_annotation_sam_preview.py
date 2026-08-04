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
