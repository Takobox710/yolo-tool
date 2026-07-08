from __future__ import annotations

import threading
from pathlib import Path
from queue import Queue

from src.ui.features.validation.page_actions import ValidationPageActionsMixin
from src.ui.features.validation.layout import build_validation_layout
from src.ui.shared.page_base import BasePage
from src.shared.qt import QPushButton, QTimer
from src.ui.shared.workers.detection import DetectionWorker


class ValidatePage(ValidationPageActionsMixin, BasePage):
    def __init__(self, app):
        super().__init__(app)
        self.detect_results = []
        self.detect_index = -1
        self.detect_stop = threading.Event()
        self.detect_worker = None
        self.is_detecting = False
        self.is_batch_detection = False
        self._all_model_paths: list[Path] = []
        self._model_display_paths: dict[str, Path] = {}
        self.source_items: list[Path] = []
        self.source_index = -1
        self.result_by_source: dict[str, dict] = {}
        self.user_selected_result = False
        self.result_nav_buttons: list[QPushButton] = []
        self.log_queue: Queue | None = None
        self.stop_requested = False
        self._build_result_navigator()
        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(150)
        self.poll_timer.timeout.connect(self.poll_validation_queue)
        build_validation_layout(self, app)

        self.mode_combo.currentTextChanged.connect(self.update_source_mode)
        self.update_source_mode(self.mode_combo.currentText())
        self.update_detection_button_text()


