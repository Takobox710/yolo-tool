from __future__ import annotations

from queue import Queue

from scr.services.runtime_service import spawn_logged_process, stop_process
from scr.ui.page_base import BasePage, Card
from scr.ui.qt import QTimer
from scr.ui.views.training_form import build_training_layout
from scr.ui.views.training_runtime import (
    finish_training,
    open_result,
    poll_training_queue,
    recover_training_state_if_process_exited,
    start_training,
    stop_training,
)
from scr.ui.views.training_state import (
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

# ===================================================================
#  Task 14: Validate page - model dropdown, first/last buttons
#  Task 9: Prevent double-start
#  Task 3: Relative paths
# ===================================================================


TrainPage.refresh_train_status = lambda self: refresh_train_status(self)
TrainPage.apply_train_status = lambda self, payload: apply_train_status(self, payload)
TrainPage.collect_config = lambda self: collect_config(self)
TrainPage._models_dir = lambda self: models_dir(self)
TrainPage._default_training_value = lambda self, key: default_training_value(self, key)
TrainPage._save_training_settings = lambda self, config: save_training_settings(self, config)
TrainPage._connect_training_persistence = lambda self: connect_training_persistence(self)
TrainPage._persist_training_text = lambda self, key: persist_training_text(self, key)
TrainPage._persist_training_value = lambda self, key, value: persist_training_value(self, key, value)
TrainPage._persist_model_selection = lambda self, _value="": persist_model_selection(self)
TrainPage._persist_augmentation = lambda self, key: persist_augmentation(self, key)
TrainPage._resolve_model_reference = lambda self, model_text: resolve_model_reference(self, model_text)
TrainPage.refresh_command_preview = lambda self: refresh_command_preview(self)
TrainPage._normalize_command_model_targets = lambda self, command: normalize_command_model_targets(self, command)
TrainPage.start = lambda self: start_training(self)
TrainPage.poll_training_queue = lambda self: poll_training_queue(self)
TrainPage.stop = lambda self: stop_training(self)
TrainPage._recover_training_state_if_process_exited = lambda self: recover_training_state_if_process_exited(self)
TrainPage._finish_training = lambda self, exit_code: finish_training(self, exit_code)
TrainPage.open_result = lambda self: open_result(self)
