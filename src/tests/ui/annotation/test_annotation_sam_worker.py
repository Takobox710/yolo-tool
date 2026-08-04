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
