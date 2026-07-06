from __future__ import annotations

from pathlib import Path
from queue import Queue
from typing import Callable

from scr.ui.qt import QMessageBox


def start_dataset_validation(
    page,
    *,
    config: dict,
    root: Path,
    build_command: Callable[[dict], list[str]],
    spawn_process: Callable,
) -> None:
    if not config["model_path"]:
        QMessageBox.information(page, "模型为空", "请选择一个用于验证的模型。")
        return
    if not config["data"] or not Path(config["data"]).exists():
        QMessageBox.information(page, "数据集 YAML 为空", "请选择有效的 data.yaml。")
        return
    page._prepare_temporary_validation_yaml(
        Path(config["data"]), config["source_scope"]
    )
    page.is_detecting = True
    page.is_batch_detection = False
    page.stop_requested = False
    page.start_det_btn.setEnabled(False)
    page.stop_det_btn.setEnabled(True)
    page.clear_active_log()
    command = build_command(config)
    page.append_active_log(" ".join(command))
    page.log_queue = Queue()
    page.app.validation_handle = spawn_process(command, str(root), page.log_queue)
    page.poll_timer.start()
    page.table.setRowCount(0)
    page.counter.setText("验证中")
    page.set_status_text("验证中")


def stop_dataset_validation(page, stop_process: Callable) -> None:
    page.stop_requested = True
    page.stop_det_btn.setEnabled(False)
    page.set_status_text("停止验证中")
    stop_process(getattr(page.app, "validation_handle", None))
    page.append_active_log("已请求停止验证。")


def poll_dataset_validation_queue(page) -> None:
    if page.log_queue is None:
        recover_dataset_validation_state(page)
        return
    while not page.log_queue.empty():
        event, payload = page.log_queue.get()
        if event == "log":
            if page.stop_requested:
                continue
            page.append_active_log(payload)
        elif event == "exit":
            finish_dataset_validation(page, payload)
            return
    recover_dataset_validation_state(page)


def recover_dataset_validation_state(page) -> None:
    handle = getattr(page.app, "validation_handle", None)
    if not page.is_detecting or handle is None or not page.is_val_mode():
        return
    exit_code = handle.process.poll()
    if exit_code is None:
        return
    finish_dataset_validation(page, exit_code)


def finish_dataset_validation(page, exit_code: int) -> None:
    page._restore_temporary_validation_yaml_if_needed()
    if page.stop_requested:
        page.append_active_log("验证已停止。")
        page.set_status_text("验证已停止")
    else:
        page.append_active_log(f"验证进程结束，退出码：{exit_code}")
        page.set_status_text("验证结束" if exit_code == 0 else "验证异常结束")
    page.poll_timer.stop()
    page.is_detecting = False
    page.stop_requested = False
    page.start_det_btn.setEnabled(True)
    page.stop_det_btn.setEnabled(False)
    page.log_queue = None
    page.app.validation_handle = None
    page.counter.setText("验证模式")
