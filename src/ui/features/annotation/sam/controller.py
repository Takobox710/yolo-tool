from __future__ import annotations

import time
from math import hypot
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal

from src.services.annotation import (
    SamModelSpec,
    find_sam_model_specs,
    preferred_sam_model,
)
from src.shared.qt import QMessageBox
from src.ui.features.annotation.sam.runtime import SamAssistRuntimeWorker
from src.ui.features.annotation.sam.hover_scheduler import SamHoverSchedulerMixin
from src.ui.features.annotation.sam.model_state import SamModelStateMixin
from src.ui.features.annotation.sam.runtime_bridge import SamRuntimeBridgeMixin


class SamAssistController(
    SamModelStateMixin,
    SamHoverSchedulerMixin,
    SamRuntimeBridgeMixin,
    QObject,
):
    state_changed = Signal()

    _HOVER_MIN_INTERVAL_MS = 50
    _HOVER_MAX_INTERVAL_MS = 120
    _HOVER_DEFAULT_INTERVAL_MS = 80
    _HOVER_EMA_ALPHA = 0.35
    _HOVER_MIN_MOVE_PX = 2.0

    def __init__(self, page) -> None:
        super().__init__(page)
        self.page = page
        self.enabled = False
        self.state = "disabled"
        self.models: list[SamModelSpec] = []
        self.selected_model: SamModelSpec | None = None
        self.model_generation = 0
        self.image_generation = 0
        self.hover_generation = 0
        self._minimum_hover_generation = 0
        self._worker: SamAssistRuntimeWorker | None = None
        self._workers: set[SamAssistRuntimeWorker] = set()
        self._model_loaded = False
        self._image_ready = False
        self._hover_payload: dict[str, Any] | None = None
        self._hover_inflight = False
        self._hover_started_at = 0.0
        self._last_hover_submit_at = 0.0
        self._hover_ema_ms: float | None = None
        self._last_hover_point: tuple[float, float] | None = None
        self._last_hover_shape = ""
        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.setInterval(self._HOVER_DEFAULT_INTERVAL_MS)
        self._hover_timer.timeout.connect(self._submit_hover)
        self.refresh_models()
        self.page.canvas.sam_hover_callback = self.request_hover
        self.page.canvas.sam_toggle_callback = self.set_enabled
        self.page.canvas.sam_image_callback = self.set_current_image
        self.page.canvas.sam_cancel_hover_callback = self.cancel_hover
