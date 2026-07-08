from __future__ import annotations

import os
from pathlib import Path
from queue import Queue

from src.shared.paths import ROOT
from src.services.runtime import spawn_logged_process, stop_process
from src.services.training import build_train_command, repair_validation_path_if_needed
from src.ui.shared.dialogs import CommandDialog
from src.shared.qt import QDialog


def _spawn_logged_process():
    from src.ui.features.training import page as training_module

    return getattr(training_module, "spawn_logged_process", spawn_logged_process)


def _stop_process():
    from src.ui.features.training import page as training_module

    return getattr(training_module, "stop_process", stop_process)


def start_training(page):
    if page.is_training:
        return
    config = page.collect_config()
    repaired = repair_validation_path_if_needed(config.get("data"))
    page._save_training_settings(config)
    command = build_train_command(config)
    command = page._normalize_command_model_targets(command)

    if page.app.settings.get("features", {}).get("custom_command_dialog", True):
        dialog = CommandDialog(command, page)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        command = page._normalize_command_model_targets(dialog.get_command())
    else:
        command = page._normalize_command_model_targets(command)

    page.is_training = True
    page.stop_requested = False
    page.start_btn.setEnabled(False)
    page.stop_btn.setEnabled(True)
    page.log.clear()
    if repaired:
        page.log.append("已自动修复 data.yaml 中未还原的 val 路径。")
    page.log.append(" ".join(command))
    page.log_queue = Queue()
    page.app.training_handle = _spawn_logged_process()(command, str(ROOT), page.log_queue)
    page.poll_timer.start(150)
    page.set_status_text("训练中")


def poll_training_queue(page):
    if page.log_queue is None:
        recover_training_state_if_process_exited(page)
        return
    while not page.log_queue.empty():
        event, payload = page.log_queue.get()
        if event == "log":
            if page.stop_requested:
                continue
            page.log.append(payload)
        elif event == "exit":
            finish_training(page, payload)
            return
    recover_training_state_if_process_exited(page)


def stop_training(page):
    if not page.is_training or page.stop_requested:
        return
    page.stop_requested = True
    page.stop_btn.setEnabled(False)
    page.set_status_text("停止训练中")
    _stop_process()(page.app.training_handle)
    page.log.append("已请求停止训练。")


def recover_training_state_if_process_exited(page):
    handle = getattr(page.app, "training_handle", None)
    if not page.is_training or handle is None:
        return
    exit_code = handle.process.poll()
    if exit_code is None:
        return
    finish_training(page, exit_code)


def finish_training(page, exit_code: int):
    if page.stop_requested:
        page.log.append("训练已停止。")
        page.set_status_text("训练已停止")
    else:
        page.log.append(f"训练进程结束，退出码：{exit_code}")
        page.set_status_text("训练结束" if exit_code == 0 else "训练异常结束")
    page.poll_timer.stop()
    page.is_training = False
    page.stop_requested = False
    page.start_btn.setEnabled(True)
    page.stop_btn.setEnabled(False)
    page.log_queue = None
    page.app.training_handle = None


def open_result(page):
    path = Path(
        page.resolve_path_text(page.edits["project"])
        if page.edits.get("project")
        else page.app.settings["paths"]["result_dir"]
    )
    if path.exists():
        os.startfile(path)


