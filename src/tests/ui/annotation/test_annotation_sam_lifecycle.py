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
