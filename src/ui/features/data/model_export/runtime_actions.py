from __future__ import annotations

import os
from pathlib import Path

from src.services.model_export import (
    build_model_export_command,
    cleanup_stale_export_workdirs,
    export_artifact_path,
    export_capability,
    resolve_export_format,
)
from src.services.runtime import spawn_structured_process, stop_process
from src.shared.paths import ROOT
from src.shared.qt import QMessageBox, QTimer


def preview_export(page) -> None:
    try:
        config = page.collect_config()
    except ValueError as exc:
        QMessageBox.warning(page, "无法预览", str(exc))
        return
    spec = resolve_export_format(config.export_format)
    capability = page._runtime_capability(spec.argument, config.precision)
    target = export_artifact_path(
        config.model_path,
        config.output_dir,
        spec.argument,
        config.precision,
    )
    overwrite = "是，执行前会要求确认" if target.exists() else "否"
    page.log.setPlainText(
        "\n".join(
            [
                f"源模型：{config.model_path}",
                f"目标格式：{spec.display_name}",
                f"模型类型：{page._current_model_kind().upper()}",
                f"导出精度：{config.precision}",
                f"目标产物：{target}",
                f"输入尺寸：{config.imgsz} x {config.imgsz}",
                f"Batch：{config.batch}",
                f"动态轴：batch={config.dynamic_batch}, height={config.dynamic_height}, width={config.dynamic_width}",
                f"NMS：{config.nms}",
                f"运行环境：{capability.runtime}",
                f"环境状态：{capability.reason}",
                f"覆盖已有结果：{overwrite}",
            ]
        )
    )


def start_export(page) -> None:
    if page.is_exporting:
        return
    try:
        config = page.collect_config()
    except ValueError as exc:
        QMessageBox.warning(page, "无法转换", str(exc))
        return
    capability = page._runtime_capability(config.export_format, config.precision)
    if not capability.available:
        QMessageBox.warning(page, "转换环境不可用", capability.reason)
        return
    target = export_artifact_path(
        config.model_path,
        config.output_dir,
        config.export_format,
        config.precision,
    )
    if target.exists():
        answer = QMessageBox.question(
            page,
            "覆盖转换结果",
            f"目标已存在：\n{target}\n\n是否在转换成功后替换它？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
    command = build_model_export_command(config, runtime_executable=capability.executable)
    page._persist_config(config)
    page.result_path = None
    page.log.clear()
    page.log.append(
        f"开始转换：{config.model_path.name} -> {resolve_export_format(config.export_format).display_name}"
    )
    from queue import Queue

    page.log_queue = Queue()
    process = spawn_structured_process(command, str(ROOT), page.log_queue)
    lease = page.context.tasks.begin(
        "model_export",
        generation=page.context.generation,
        stop=lambda: stop_process(process),
    )
    if lease is None:
        stop_process(process)
        return
    page._export_process = process
    page._export_lease = lease
    page.is_exporting = True
    page.stop_requested = False
    page._set_running_state(True)
    page.poll_timer.start(150)


def poll_export_queue(page) -> None:
    if page.log_queue is None:
        return
    while not page.log_queue.empty():
        kind, payload = page.log_queue.get()
        if kind == "log":
            page.log.append(str(payload))
        elif kind == "structured":
            event = payload.get("event")
            if event == "progress":
                page.log.append(str(payload.get("message", "")))
            elif event == "done":
                page.result_path = Path(str(payload.get("result_path", "")))
            elif event == "error":
                page.log.append(f"转换失败：{payload.get('message', '未知错误')}")
        elif kind == "exit":
            finish_export(page, int(payload))
            return


def stop_export(page) -> None:
    if not page.is_exporting or page.stop_requested:
        return
    page.stop_requested = True
    page.stop_btn.setEnabled(False)
    stop_process(page._export_process)
    page.log.append("已请求停止转换。")


def finish_export(page, exit_code: int) -> None:
    page.poll_timer.stop()
    try:
        cleanup_stale_export_workdirs(page.collect_config().output_dir)
    except ValueError:
        pass
    if page.stop_requested:
        page.log.append("模型转换已停止。")
    elif exit_code == 0 and page.result_path:
        page.log.append(f"模型转换完成：{page.result_path}")
    else:
        page.log.append(f"模型转换异常结束，退出码：{exit_code}")
    page.is_exporting = False
    page.stop_requested = False
    page.log_queue = None
    page.context.tasks.finish(page._export_lease)
    page._export_lease = None
    page._export_process = None
    page._set_running_state(False)
    page.update_environment_status()


def set_running_state(page, running: bool) -> None:
    for widget in (
        page.model_combo,
        page.output_edit,
        page.format_combo,
        page.precision_combo,
        page.imgsz_edit,
        page.batch_spin,
        page.dynamic_box,
        page.nms_box,
        page.int8_box,
        page.opset_box,
        page.workspace_box,
        page.optimize_box,
        page.dynamic_input_check,
        page.calibration_pack_btn,
        page.onnx_simplify_btn,
        page.onnx_nms_btn,
        page.onnx_agnostic_btn,
        page.onnx_dynamic_batch_check,
        page.onnx_dynamic_size_check,
        page.onnx_conf_spin,
        page.onnx_iou_spin,
        page.onnx_max_det_spin,
        page.onnx_opset_spin,
        page.preview_btn,
        page.start_btn,
        page.install_btn,
    ):
        widget.setEnabled(not running)
    page.stop_btn.setEnabled(running)


def open_output_dir(page) -> None:
    root = Path(page.resolve_path_text(page.output_edit))
    root.mkdir(parents=True, exist_ok=True)
    os.startfile(root)


def runtime_capability(page, export_format: str, precision: str):
    return page._runtime_capability_for(
        export_format, page._current_model_kind(), precision
    )


def runtime_capability_for(page, export_format: str, model_kind: str, precision: str):
    try:
        return export_capability(
            export_format,
            model_kind=model_kind,
            precision=precision,
        )
    except TypeError:
        return export_capability(export_format)
