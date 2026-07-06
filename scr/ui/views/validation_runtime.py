from __future__ import annotations

import os
from importlib import import_module
from pathlib import Path

from scr.paths import ROOT
from scr.services.detection_service import is_live_source_mode
from scr.services.runtime_service import spawn_logged_process, stop_process
from scr.services.training_service import build_val_command
from scr.ui.qt import QMessageBox
from scr.ui.views.validation_dataset import (
    finish_dataset_validation,
    poll_dataset_validation_queue,
    recover_dataset_validation_state,
    start_dataset_validation as start_dataset_validation_task,
    stop_dataset_validation,
)
from scr.ui.workers import DetectionWorker


def _detection_worker_class():
    module = import_module("scr.ui.views.validation")
    return getattr(module, "DetectionWorker", DetectionWorker)


def _connect_detection_worker(page, worker) -> None:
    worker.progress.connect(page.append_active_log)
    worker.result_payload.connect(page.handle_result)
    worker.finished_with_results.connect(page.apply_detect_done)
    worker.failed.connect(page.apply_detect_error)
    worker.finished.connect(lambda: _clear_detection_worker(page, worker))


def _clear_detection_worker(page, worker) -> None:
    if getattr(page, "detect_worker", None) is worker:
        page.detect_worker = None


def start_detection(page):
    if page.is_detecting:
        return
    if page.is_val_mode():
        page.start_dataset_validation()
        return
    config = page.detection_config_or_warn()
    if config is None:
        return
    page.refresh_source_items()
    if page.mode_combo.currentText() != "摄像头" and not page.source_items:
        QMessageBox.information(
            page,
            "输入源为空",
            "请先选择有效的输入源，或确认所选来源下存在图片/视频。",
        )
        return
    if page.mode_combo.currentText() == "图片/视频":
        if not page.source_items:
            QMessageBox.information(
                page,
                "输入源为空",
                "请先选择有效的输入源，或确认 data.yaml 中所选来源下存在图片/视频。",
            )
            return
        page.source_index = max(0, min(page.source_index, len(page.source_items) - 1))
        page.start_current_source_detection()
        return
    page.is_detecting = True
    page.start_det_btn.setEnabled(False)
    page.stop_det_btn.setEnabled(True)
    page.detect_log.clear()
    page.detect_stop.clear()
    page.detect_results.clear()
    page.result_by_source.clear()
    page.user_selected_result = False
    page.is_batch_detection = not is_live_source_mode(page.mode_combo.currentText())
    page.detect_index = -1
    page.clear_active_log()
    page.append_active_log(
        f"开始检测：模型 {Path(config['model_path']).name}，输入源 {config['source_mode']}。"
    )
    page.counter.setText(
        "实时预览" if is_live_source_mode(page.mode_combo.currentText()) else "0/0"
    )
    page.table.setRowCount(0)
    page.set_status_text("检测中")
    page.detect_worker = _detection_worker_class()(config, page.detect_stop)
    _connect_detection_worker(page, page.detect_worker)
    page.detect_worker.start()


def start_dataset_validation(page):
    start_dataset_validation_task(
        page,
        config=page.config(),
        root=ROOT,
        build_command=build_val_command,
        spawn_process=spawn_logged_process,
    )


def start_current_source_detection(page):
    if not page.source_items:
        return
    page.source_index = max(0, min(page.source_index, len(page.source_items) - 1))
    page.start_single_detection(page.source_items[page.source_index])


def start_single_detection(page, path: Path):
    if page.is_detecting:
        return
    page.refresh_source_items()
    config = page.detection_config_or_warn()
    if config is None:
        return
    source_key = str(Path(path).resolve())
    cached = page.result_by_source.get(source_key)
    if cached:
        page.detect_index = (
            page.detect_results.index(cached)
            if cached in page.detect_results
            else page.detect_index
        )
        page.show_detection_payload(cached)
        return
    page.is_detecting = True
    page.is_batch_detection = False
    page.start_det_btn.setEnabled(False)
    page.stop_det_btn.setEnabled(True)
    page.detect_stop.clear()
    page.set_status_text("检测中")
    page.append_active_log(
        f"开始检测：模型 {Path(config['model_path']).name}，输入源 {path.name}。"
    )
    page.detect_worker = _detection_worker_class()(
        page.single_file_config(path, config), page.detect_stop
    )
    _connect_detection_worker(page, page.detect_worker)
    page.detect_worker.start()


def apply_detect_done(page, _results):
    if page.detect_stop.is_set():
        page.append_active_log("检测已停止。")
        page.set_status_text("检测已停止")
    else:
        page.append_active_log("检测任务结束。")
        page.set_status_text("检测结束")
    page.is_detecting = False
    page.start_det_btn.setEnabled(True)
    page.stop_det_btn.setEnabled(False)
    page.detect_stop.clear()


def apply_detect_error(page, message):
    page.append_active_log(message)
    page.set_status_text("检测异常")
    page.is_detecting = False
    page.start_det_btn.setEnabled(True)
    page.stop_det_btn.setEnabled(False)
    page.detect_stop.clear()


def stop_detection(page):
    if not page.is_detecting:
        return
    if page.is_val_mode():
        stop_dataset_validation(page, stop_process)
        return
    page.detect_stop.set()
    page.stop_det_btn.setEnabled(False)
    worker = getattr(page, "detect_worker", None)
    request_stop = getattr(worker, "request_stop", None)
    if callable(request_stop):
        request_stop()
    page.append_active_log("已请求停止检测。")
    page.set_status_text("停止检测中")


def poll_validation_queue(page):
    poll_dataset_validation_queue(page)


def recover_validation_state_if_process_exited(page):
    recover_dataset_validation_state(page)


def finish_dataset_validation_for_page(page, exit_code: int):
    finish_dataset_validation(page, exit_code)


def open_detection_save_dir(page):
    save_dir = Path(page.resolve_path_text(page.save_edit))
    save_dir.mkdir(parents=True, exist_ok=True)
    os.startfile(save_dir)
