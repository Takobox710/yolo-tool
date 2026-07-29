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




def test_sam_runtime_worker_keeps_only_latest_waiting_prediction():
    from src.ui.features.annotation.sam.runtime import SamAssistRuntimeWorker

    worker = SamAssistRuntimeWorker()
    sent = []

    def fake_send(action, payload):
        sent.append((action, dict(payload)))
        return f"request-{len(sent)}"

    worker._send = fake_send
    worker._handle_command("predict_point", {"x": 1})
    worker._handle_command("predict_point", {"x": 2})
    worker._handle_command("predict_point", {"x": 3})

    assert sent == [("predict_point", {"x": 1})]
    worker._prediction_request_id = ""
    worker._send_latest_prediction()
    assert sent == [
        ("predict_point", {"x": 1}),
        ("predict_point", {"x": 3}),
    ]




def test_sam_controller_adapts_movement_without_waiting_for_mouse_stop(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AnnotationPage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )
    page = AnnotationPage(fake_app)
    controller = page.sam_assist
    sent = []
    controller.enabled = True
    controller.state = "ready"
    controller.model_generation = 2
    controller.image_generation = 3
    controller._worker = SimpleNamespace(predict_point=lambda payload: sent.append(payload))

    controller.request_hover((10.0, 11.0), "rect")
    controller.request_hover((20.0, 21.0), "rect")
    controller.request_hover((30.0, 31.0), "rect")
    controller.request_hover((30.5, 31.0), "rect")

    assert [(item["x"], item["y"]) for item in sent] == [(10.0, 11.0)]
    assert sent[0]["multimask_output"] is False
    assert sent[0]["minimum_score"] == 0.0
    assert sent[0]["minimum_area"] == 4
    assert sent[0]["simplification_ratio"] == 0.002
    assert controller._hover_inflight is True
    assert controller._hover_timer.isActive() is False
    assert controller._hover_payload["x"] == 30.0

    controller._last_hover_submit_at -= 1.0
    controller._finish_hover_request()

    assert [(item["x"], item["y"]) for item in sent] == [
        (10.0, 11.0),
        (30.0, 31.0),
    ]
    assert controller._hover_inflight is True

    controller._hover_ema_ms = 30.0
    assert controller._hover_interval_ms() == 50
    controller._hover_ema_ms = 100.0
    assert controller._hover_interval_ms() == 75
    controller._hover_ema_ms = 300.0
    assert controller._hover_interval_ms() == 120




def test_sam_controller_displays_latest_completed_frame_while_mouse_moves(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.annotation import EditableAnnotation
    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AnnotationPage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )
    page = AnnotationPage(fake_app)
    controller = page.sam_assist
    page.canvas.set_draw_shape("rect")
    controller.enabled = True
    controller.state = "predicting"
    controller.model_generation = 4
    controller.image_generation = 5
    controller.hover_generation = 7
    page.canvas.sam_preview_annotation = EditableAnnotation(
        0,
        "rect",
        [(1.0, 1.0), (2.0, 1.0), (2.0, 2.0), (1.0, 2.0)],
    )

    controller._handle_response(
        "predict_point",
        {
            "model_generation": 4,
            "image_generation": 5,
            "hover_generation": 6,
            "shape": "rect",
        },
        {
            "geometry": {
                "rectangle": [[10, 10], [40, 10], [40, 40], [10, 40]],
            }
        },
    )

    assert page.canvas.sam_preview_generation == 6
    assert page.canvas.sam_preview_annotation.points[0] == (10.0, 10.0)
    assert controller.state == "predicting"




def test_sam_toggle_off_keeps_runtime_until_page_shutdown(tmp_path):
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
    controller = page.sam_assist

    class FakeWorker:
        def __init__(self):
            self.shutdown_calls = 0

        def shutdown(self):
            self.shutdown_calls += 1

    worker = FakeWorker()
    controller.enabled = True
    controller._worker = worker
    controller._model_loaded = True
    controller._image_ready = True

    assert controller.set_enabled(False) is False
    assert controller._worker is worker
    assert worker.shutdown_calls == 0

    assert controller.set_enabled(True) is True
    assert controller._worker is worker
    assert worker.shutdown_calls == 0

    controller.shutdown(wait=False)
    assert worker.shutdown_calls == 1




def test_sam_runtime_worker_requests_graceful_shutdown_before_stop(monkeypatch):
    from src.ui.features.annotation.sam.runtime import SamAssistRuntimeWorker
    import src.ui.features.annotation.sam.runtime as sam_runtime

    writes = []
    stops = []

    class FakeStdin:
        def write(self, value):
            writes.append(value)

        def flush(self):
            return None

    class FakeProcess:
        stdin = FakeStdin()

        def poll(self):
            return None

        def wait(self, timeout):
            assert timeout == 0.75
            return 0

    handle = SimpleNamespace(process=FakeProcess())
    worker = SamAssistRuntimeWorker()
    worker._handle = handle
    monkeypatch.setattr(sam_runtime, "stop_process", lambda current: stops.append(current))

    worker._handle_command("shutdown", {})

    assert worker._shutdown_requested is True
    assert len(writes) == 1
    assert '"action": "shutdown"' in writes[0]
    assert stops == [handle]




def test_sam_controller_ignores_stale_worker_and_hover_failures(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AnnotationPage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )
    page = AnnotationPage(fake_app)
    controller = page.sam_assist
    current_worker = object()
    stale_worker = object()
    controller.enabled = True
    controller.state = "predicting"
    controller._worker = current_worker
    controller.model_generation = 4
    controller.image_generation = 5
    controller.hover_generation = 6

    controller._handle_runtime_failure(
        "old worker failed",
        worker=stale_worker,
        model_generation=3,
    )
    controller._handle_request_failure(
        "predict_point",
        {
            "model_generation": 4,
            "image_generation": 5,
            "hover_generation": 5,
        },
        "old hover failed",
    )

    assert controller.enabled is True
    assert controller.state == "predicting"




def test_sam_model_reload_clears_preview_and_pending_hover(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.annotation import EditableAnnotation
    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AnnotationPage
    import src.ui.features.annotation.sam.controller as sam_controller

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )
    page = AnnotationPage(fake_app)
    controller = page.sam_assist

    class FakeWorker:
        def __init__(self, _parent):
            self.response_received = SimpleNamespace(connect=lambda _callback: None)
            self.request_failed = SimpleNamespace(connect=lambda _callback: None)
            self.runtime_failed = SimpleNamespace(connect=lambda _callback: None)
            self.log_received = SimpleNamespace(connect=lambda _callback: None)
            self.finished = SimpleNamespace(connect=lambda _callback: None)

        def start(self):
            return None

        def load_model(self, _payload):
            return None

    monkeypatch.setattr(sam_controller, "SamAssistRuntimeWorker", FakeWorker)
    controller.enabled = True
    controller._hover_payload = {"x": 1.0}
    controller._hover_timer.start()
    page.canvas.sam_preview_annotation = EditableAnnotation(
        0,
        "rect",
        [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)],
    )

    controller._load_selected_model()

    assert controller._hover_payload is None
    assert controller._hover_timer.isActive() is False
    assert page.canvas.sam_preview_annotation is None




def test_sam_controller_cancel_hover_invalidates_inflight_result(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AnnotationPage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
    )
    page = AnnotationPage(fake_app)
    controller = page.sam_assist
    page.canvas.set_draw_shape("rect")
    controller.enabled = True
    controller.state = "predicting"
    controller.hover_generation = 8
    controller._hover_payload = {"hover_generation": 8}
    controller._hover_timer.start()

    controller.cancel_hover()

    assert controller.hover_generation == 9
    assert controller._hover_payload is None
    assert controller._hover_timer.isActive() is False
    assert controller.state == "ready"

    controller._handle_response(
        "predict_point",
        {
            "model_generation": controller.model_generation,
            "image_generation": controller.image_generation,
            "hover_generation": 8,
            "shape": "rect",
        },
        {
            "geometry": {
                "rectangle": [[10, 10], [40, 10], [40, 40], [10, 40]],
            }
        },
    )

    assert page.canvas.sam_preview_annotation is None


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




