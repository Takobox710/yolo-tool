from __future__ import annotations

from queue import Queue

from src.services.runtime import spawn_logged_process, stop_process
from src.ui.shared.page_base import BasePage, Card
from src.shared.qt import QTimer
from src.ui.features.training.form import build_training_layout
from src.ui.features.training.runtime import (
    finish_training,
    open_result,
    poll_training_queue,
    recover_training_state_if_process_exited,
    start_training,
    stop_training,
)
from src.ui.features.training.state import (
    apply_train_status,
    collect_config,
    connect_training_persistence,
    default_training_value,
    models_dir,
    normalize_command_model_targets,
    persist_augmentation,
    persist_model_selection,
    persist_training_text,
    persist_training_value,
    refresh_command_preview,
    refresh_train_status,
    resolve_model_reference,
    save_training_settings,
)

class TrainPage(BasePage):
    def __init__(self, app):
        super().__init__(app)
        self.edits = {}
        self.checks = {}
        self.metric_labels = {}
        self.log_queue: Queue | None = None
        self.is_training = False
        self.stop_requested = False
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.poll_training_queue)
        self.train_status_timer = QTimer(self)
        self.train_status_timer.timeout.connect(self.refresh_train_status)
        self.train_status_timer.setInterval(500)
        build_training_layout(self)
        self._connect_training_persistence()
        self.refresh_command_preview()

    def on_show(self):
        if not self.train_status_timer.isActive():
            self.train_status_timer.start()
        for metric in self.metric_labels.values():
            metric.setText("检测中...")
        self.refresh_train_status()

    def on_hide(self):
        self.train_status_timer.stop()

    def refresh_train_status(self):
        return refresh_train_status(self)

    def apply_train_status(self, payload):
        return apply_train_status(self, payload)

    def collect_config(self):
        return collect_config(self)

    def _models_dir(self):
        return models_dir(self)

    def _default_training_value(self, key):
        return default_training_value(self, key)

    def _save_training_settings(self, config):
        return save_training_settings(self, config)

    def _connect_training_persistence(self):
        return connect_training_persistence(self)

    def _persist_training_text(self, key):
        return persist_training_text(self, key)

    def _persist_training_value(self, key, value):
        return persist_training_value(self, key, value)

    def _persist_model_selection(self, _value=""):
        return persist_model_selection(self)

    def _persist_augmentation(self, key):
        return persist_augmentation(self, key)

    def _resolve_model_reference(self, model_text):
        return resolve_model_reference(self, model_text)

    def refresh_command_preview(self):
        return refresh_command_preview(self)

    def _normalize_command_model_targets(self, command):
        return normalize_command_model_targets(self, command)

    def start(self):
        return start_training(self)

    def poll_training_queue(self):
        return poll_training_queue(self)

    def stop(self):
        return stop_training(self)

    def _recover_training_state_if_process_exited(self):
        return recover_training_state_if_process_exited(self)

    def _finish_training(self, exit_code):
        return finish_training(self, exit_code)

    def open_result(self):
        return open_result(self)


