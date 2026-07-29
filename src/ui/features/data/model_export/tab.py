from __future__ import annotations

import os
from pathlib import Path
from queue import Queue

from src.services.model_export import (
    ModelExportConfig,
    build_model_export_command,
    cleanup_stale_export_workdirs,
    export_artifact_path,
    export_capability,
    export_display_names,
    export_model_display_path,
    find_export_model_paths,
    resolve_export_format,
)
from src.services.runtime import spawn_structured_process, stop_process
from src.shared.paths import ROOT
from src.shared.qt import (
    QFileDialog,
    QLabel,
    QMessageBox,
    QTimer,
)
from src.ui.shared.page_base import BasePage
from src.ui.features.data.model_export.state import ModelExportStateMixin
from src.ui.features.data.model_export.layout import build_model_export_layout
from src.ui.shared.model_export_package import ModelExportPackageDropMixin


class ModelExportTab(
    ModelExportPackageDropMixin,
    ModelExportStateMixin,
    BasePage,
):
    def __init__(self, context):
        super().__init__(context)
        self.is_exporting = False
        self.stop_requested = False
        self.log_queue: Queue | None = None
        self.result_path: Path | None = None
        self._export_process = None
        self._export_lease = None
        self._model_display_paths: dict[str, Path] = {}
        self.setup_model_export_package_drop()
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.poll_export_queue)

        build_model_export_layout(self)

        self.refresh_model_choices()
        self._connect_persistence()
        self.format_combo.currentTextChanged.connect(self.update_environment_status)
        self.update_environment_status()
        self.finalize_model_export_package_drop()

    def choose_model(self, combo):
        start = self.project_root() / "data" / "models"
        start.mkdir(parents=True, exist_ok=True)
        path, _ = QFileDialog.getOpenFileName(
            self, "选择模型文件", str(start), "PyTorch 模型 (*.pt);;所有文件 (*)"
        )
        if path:
            resolved = Path(path).resolve()
            display = self._model_display_path(resolved)
            self._model_display_paths[display] = resolved
            combo.setCurrentText(display)

    def refresh_model_choices(self):
        current = self.model_combo.currentText()
        show_last = self.context.settings.features.show_last_training_models
        paths = find_export_model_paths(
            self.project_root(), show_last_training_models=show_last
        )
        self._model_display_paths = {
            export_model_display_path(path, self.project_root()): path for path in paths
        }
        choices = list(self._model_display_paths)
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        self.model_combo.addItems(choices)
        if current:
            self.model_combo.setCurrentText(current)
        elif choices:
            self.model_combo.setCurrentIndex(0)
        self.model_combo.blockSignals(False)

    def _model_display_path(self, value: str | Path) -> str:
        if not value:
            return ""
        path = Path(self.resolve_project_value(str(value)))
        if path.is_file() and path.parent.name.lower() == "weights":
            display = export_model_display_path(path, self.project_root())
            self._model_display_paths[display] = path
            return display
        return self.display_path(value)

    def collect_config(self) -> ModelExportConfig:
        model_text = self.model_combo.currentText().strip()
        model_path = Path(self.model_path_from_text(model_text))
        try:
            imgsz = int(self.imgsz_edit.text())
        except ValueError as exc:
            raise ValueError("输入尺寸必须是整数。") from exc
        if imgsz < 32 or imgsz % 32:
            raise ValueError("输入尺寸必须是不小于 32 的 32 倍数。")
        if not model_path.is_file() or model_path.suffix.lower() != ".pt":
            raise ValueError("请选择存在的 .pt 模型文件。")
        spec = resolve_export_format(self.format_combo.currentText())
        output_root = Path(self.resolve_path_text(self.output_edit))
        return ModelExportConfig(
            model_path=model_path,
            output_dir=output_root / model_path.stem,
            export_format=spec.argument,
            imgsz=imgsz,
            simplify=self.simplify_check.isChecked(),
        )

    def model_path_from_text(self, value: str) -> str:
        path = self._model_display_paths.get(str(value).strip())
        if path is not None:
            return str(path)
        return self.resolve_project_value(value)

    def resolve_project_value(self, value: str) -> str:
        path = Path(os.path.expandvars(value)).expanduser()
        return str(path if path.is_absolute() else (self.project_root() / path).resolve())

    def update_environment_status(self, *_args):
        spec = resolve_export_format(self.format_combo.currentText())
        capability = export_capability(spec.argument)
        prefix = "可用" if capability.available else "不可用"
        self.environment_status.setText(
            f"{spec.display_name}：{prefix} | {capability.runtime} | {capability.reason}"
        )
        self.simplify_check.setEnabled(spec.argument in {"onnx", "engine"} and not self.is_exporting)

    def preview_export(self):
        try:
            config = self.collect_config()
        except ValueError as exc:
            QMessageBox.warning(self, "无法预览", str(exc))
            return
        spec = resolve_export_format(config.export_format)
        capability = export_capability(spec.argument)
        target = export_artifact_path(config.model_path, config.output_dir, spec.argument)
        overwrite = "是，执行前会要求确认" if target.exists() else "否"
        self.log.setPlainText(
            "\n".join(
                [
                    f"源模型：{config.model_path}",
                    f"目标格式：{spec.display_name}",
                    f"目标产物：{target}",
                    f"输入尺寸：{config.imgsz} x {config.imgsz}",
                    f"运行环境：{capability.runtime}",
                    f"环境状态：{capability.reason}",
                    f"覆盖已有结果：{overwrite}",
                ]
            )
        )

    def start_export(self):
        if self.is_exporting:
            return
        try:
            config = self.collect_config()
        except ValueError as exc:
            QMessageBox.warning(self, "无法转换", str(exc))
            return
        capability = export_capability(config.export_format)
        if not capability.available:
            QMessageBox.warning(self, "转换环境不可用", capability.reason)
            return
        target = export_artifact_path(config.model_path, config.output_dir, config.export_format)
        if target.exists():
            answer = QMessageBox.question(
                self,
                "覆盖转换结果",
                f"目标已存在：\n{target}\n\n是否在转换成功后替换它？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        command = build_model_export_command(config, runtime_executable=capability.executable)
        self._persist_config(config)
        self.result_path = None
        self.log.clear()
        self.log.append(f"开始转换：{config.model_path.name} -> {resolve_export_format(config.export_format).display_name}")
        self.log_queue = Queue()
        process = spawn_structured_process(command, str(ROOT), self.log_queue)
        lease = self.context.tasks.begin(
            "model_export",
            generation=self.context.generation,
            stop=lambda: stop_process(process),
        )
        if lease is None:
            stop_process(process)
            return
        self._export_process = process
        self._export_lease = lease
        self.is_exporting = True
        self.stop_requested = False
        self._set_running_state(True)
        self.poll_timer.start(150)

    def poll_export_queue(self):
        if self.log_queue is None:
            return
        while not self.log_queue.empty():
            kind, payload = self.log_queue.get()
            if kind == "log":
                self.log.append(str(payload))
            elif kind == "structured":
                event = payload.get("event")
                if event == "progress":
                    self.log.append(str(payload.get("message", "")))
                elif event == "done":
                    self.result_path = Path(str(payload.get("result_path", "")))
                elif event == "error":
                    self.log.append(f"转换失败：{payload.get('message', '未知错误')}")
            elif kind == "exit":
                self.finish_export(int(payload))
                return

    def stop_export(self):
        if not self.is_exporting or self.stop_requested:
            return
        self.stop_requested = True
        self.stop_btn.setEnabled(False)
        stop_process(self._export_process)
        self.log.append("已请求停止转换。")

    def finish_export(self, exit_code: int):
        self.poll_timer.stop()
        try:
            cleanup_stale_export_workdirs(self.collect_config().output_dir)
        except ValueError:
            pass
        if self.stop_requested:
            self.log.append("模型转换已停止。")
        elif exit_code == 0 and self.result_path:
            self.log.append(f"模型转换完成：{self.result_path}")
        else:
            self.log.append(f"模型转换异常结束，退出码：{exit_code}")
        self.is_exporting = False
        self.stop_requested = False
        self.log_queue = None
        self.context.tasks.finish(self._export_lease)
        self._export_lease = None
        self._export_process = None
        self._set_running_state(False)
        self.update_environment_status()

    def _set_running_state(self, running: bool):
        for widget in (
            self.model_combo,
            self.output_edit,
            self.format_combo,
            self.imgsz_edit,
            self.preview_btn,
            self.start_btn,
            self.install_btn,
        ):
            widget.setEnabled(not running)
        self.stop_btn.setEnabled(running)

    def open_output_dir(self):
        root = Path(self.resolve_path_text(self.output_edit))
        root.mkdir(parents=True, exist_ok=True)
        os.startfile(root)
