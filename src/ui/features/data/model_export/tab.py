from __future__ import annotations

import os
from pathlib import Path
from queue import Queue

from src.services.model_export import (
    ModelExportConfig,
    build_model_export_command,
    capabilities_for,
    cleanup_stale_export_workdirs,
    download_generic_calibration_pack,
    export_artifact_path,
    export_capability,
    export_display_names,
    export_model_display_path,
    find_export_model_paths,
    model_kind_from_path,
    generic_calibration_pack_path,
    normalize_model_export_config,
    resolve_export_format,
    validate_model_export_config,
    validate_model_export_source,
)
from src.services.runtime import spawn_structured_process, stop_process
from src.shared.paths import ROOT
from src.shared.qt import (
    QFileDialog,
    QMessageBox,
    QTimer,
)
from src.ui.shared.page_base import BasePage
from src.ui.shared.workers import Worker
from src.ui.features.data.model_export.state import ModelExportStateMixin
from src.ui.features.data.model_export.layout import (
    build_model_export_layout,
    update_model_export_card_ratio,
)
from src.ui.features.data.model_export.registry import option_keys_for
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
        self._format_option_cache: dict[str, dict] = {}
        self._format_switching = False
        self._active_format_argument = resolve_export_format(
            self.context.settings.model_export.format
        ).argument
        self.log_queue: Queue | None = None
        self.result_path: Path | None = None
        self._export_process = None
        self._export_lease = None
        self._calibration_worker: Worker | None = None
        self._model_display_paths: dict[str, Path] = {}
        self.setup_model_export_package_drop()
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.poll_export_queue)

        build_model_export_layout(self)

        self.refresh_model_choices()
        self._connect_persistence()
        self.format_combo.currentTextChanged.connect(self.update_environment_status)
        self.model_combo.currentTextChanged.connect(self.update_option_visibility)
        self.update_environment_status()
        self.update_option_visibility()
        self.finalize_model_export_package_drop()
        QTimer.singleShot(0, self, self._reflow_layout)

    def _reflow_layout(self):
        if getattr(self, "_reflowing_layout", False):
            return
        self._reflowing_layout = True
        try:
            for widget in (self, self.onnx_top_box, self.source_card, self.inference_card):
                widget.updateGeometry()
                layout = widget.layout
                if callable(layout):
                    layout = layout()
                if layout is not None:
                    layout.invalidate()
            self.layout().activate()
            update_model_export_card_ratio(self)
            self.layout().activate()
        finally:
            self._reflowing_layout = False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reflow_layout()

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
            self.project_root(),
            show_last_training_models=show_last,
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
        self.update_option_visibility()

    def _model_display_path(self, value: str | Path) -> str:
        if not value:
            return ""
        path = Path(self.resolve_project_value(str(value)))
        if path.is_file() and path.parent.name.lower() == "weights":
            display = export_model_display_path(path, self.project_root())
            self._model_display_paths[display] = path
            return display
        return self.display_path(value)

    def choose_calibration_data(self, edit):
        current = self.resolve_path_text(edit) if edit.text() else str(self.project_root())
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择校准数据",
            current,
            "数据集或图片列表 (*.yaml *.yml *.txt);;所有文件 (*)",
        )
        if path:
            edit.setText(self.display_path(path))
            return
        path = QFileDialog.getExistingDirectory(self, "选择校准图片目录", current)
        if path:
            edit.setText(self.display_path(path))

    def download_generic_calibration_pack(self):
        if self._calibration_worker is not None:
            return
        existing = generic_calibration_pack_path()
        if existing is not None:
            self.calibration_data_edit.setText(self.display_path(existing))
            self.log.append(f"通用校准集已就绪：{existing}")
            return
        self.calibration_pack_btn.setEnabled(False)
        self.calibration_pack_progress.setValue(0)
        self.calibration_pack_progress.setVisible(True)
        worker = Worker(
            "generic_calibration_pack",
            lambda report: download_generic_calibration_pack(
                progress=lambda downloaded, total: report(
                    "下载通用校准集",
                    int(downloaded * 100 / total) if total else 0,
                )
            ),
            accepts_progress=True,
        )
        self._calibration_worker = worker
        workers = getattr(self.context, "workers", None)
        if isinstance(workers, list):
            workers.append(worker)
        worker.progress.connect(self._calibration_pack_progress)
        worker.finished_with_payload.connect(self._apply_calibration_pack_result)
        worker.finished.connect(lambda: self._clear_calibration_worker(worker))
        worker.start()

    def _calibration_pack_progress(self, message: str, value: int) -> None:
        self.calibration_pack_progress.setFormat(f"{message} %p%")
        self.calibration_pack_progress.setValue(value)

    def _apply_calibration_pack_result(self, _kind: str, payload) -> None:
        if isinstance(payload, dict) and payload.get("error"):
            self.log.append(f"获取通用校准集失败：{payload['error']}")
            return
        path = Path(str(payload))
        self.calibration_data_edit.setText(self.display_path(path))
        self.calibration_pack_progress.setValue(100)
        self.log.append(f"通用校准集已就绪：{path}")

    def _clear_calibration_worker(self, worker: Worker) -> None:
        workers = getattr(self.context, "workers", None)
        if isinstance(workers, list) and worker in workers:
            workers.remove(worker)
        if self._calibration_worker is worker:
            self._calibration_worker = None
        self.calibration_pack_btn.setEnabled(not self.is_exporting)
        self.calibration_pack_progress.setVisible(False)

    def collect_config(self) -> ModelExportConfig:
        model_text = self.model_combo.currentText().strip()
        model_path = Path(self.model_path_from_text(model_text))
        if not model_path.is_file() or model_path.suffix.lower() != ".pt":
            raise ValueError("请选择存在的 .pt 模型文件。")
        spec = resolve_export_format(self.format_combo.currentText())
        model_kind = model_kind_from_path(model_path)
        if model_kind == "sam2":
            imgsz = 1024
        else:
            try:
                imgsz = int(self.imgsz_edit.text())
            except ValueError as exc:
                raise ValueError("输入尺寸必须是整数。") from exc
            if imgsz < 32 or imgsz % 32:
                raise ValueError("输入尺寸必须是不小于 32 的 32 倍数。")
        validate_model_export_source(model_path, spec.argument)
        output_root = Path(self.resolve_path_text(self.output_edit))
        precision = {"FP16": "fp16", "INT8": "int8"}.get(
            self.precision_combo.currentText(), "fp32"
        )
        calibration_data = self.resolve_path_text(self.calibration_data_edit)
        if spec.argument == "onnx":
            dynamic_batch = self.onnx_dynamic_batch_check.isChecked()
            dynamic_height = self.onnx_dynamic_size_check.isChecked()
            dynamic_width = self.onnx_dynamic_size_check.isChecked()
        else:
            dynamic_input = self.dynamic_input_check.isChecked()
            dynamic_batch = (
                dynamic_input
                if self._uses_unified_dynamic_input(spec.argument, model_kind)
                else self.dynamic_batch_check.isChecked()
            )
            dynamic_height = (
                dynamic_input
                if self._uses_unified_dynamic_input(spec.argument, model_kind)
                else self.dynamic_height_check.isChecked()
            )
            dynamic_width = (
                dynamic_input
                if self._uses_unified_dynamic_input(spec.argument, model_kind)
                else self.dynamic_width_check.isChecked()
            )
        config = ModelExportConfig(
            model_path=model_path,
            output_dir=output_root / model_path.stem,
            export_format=spec.argument,
            imgsz=imgsz,
            simplify=self.simplify_check.isChecked(),
            precision=precision,
            batch=1 if model_kind == "sam2" else self.batch_spin.value(),
            dynamic_batch=dynamic_batch,
            dynamic_height=dynamic_height,
            dynamic_width=dynamic_width,
            nms=self.nms_check.isChecked(),
            nms_conf=self.conf_spin.value(),
            nms_iou=self.iou_spin.value(),
            nms_max_det=self.max_det_spin.value(),
            agnostic_nms=self.agnostic_nms_check.isChecked(),
            opset=self.opset_spin.value() or None,
            workspace=self.workspace_spin.value(),
            optimize=self.optimize_check.isChecked(),
            calibration_data=calibration_data,
            calibration_samples=self.calibration_samples_spin.value(),
            validate_quantized=self.validate_quantized_check.isChecked(),
            validation_samples=self.validation_samples_spin.value(),
        )
        config = normalize_model_export_config(config, model_kind=model_kind)
        return validate_model_export_config(config, model_kind=model_kind)

    def model_path_from_text(self, value: str) -> str:
        path = self._model_display_paths.get(str(value).strip())
        if path is not None:
            return str(path)
        return self.resolve_project_value(value)

    def resolve_project_value(self, value: str) -> str:
        path = Path(os.path.expandvars(value)).expanduser()
        return str(path if path.is_absolute() else (self.project_root() / path).resolve())

    def update_environment_status(self, *_args):
        # 保留旧调用点兼容性；环境信息只在预览和日志中呈现。
        self.update_option_visibility()

    def update_option_visibility(self, *_args):
        spec = resolve_export_format(self.format_combo.currentText())
        model_kind = self._current_model_kind()
        if model_kind == "sam2" and spec.argument != "onnx":
            self.format_combo.blockSignals(True)
            self.format_combo.setCurrentText("ONNX")
            self.format_combo.blockSignals(False)
            self.update_setting("model_export", "format", value="onnx")
            self._active_format_argument = "onnx"
            spec = resolve_export_format("onnx")
        capabilities = capabilities_for(spec.argument, model_kind)
        is_onnx = spec.argument == "onnx"
        option_keys = set(option_keys_for(spec.argument))
        self._update_format_availability(model_kind)
        self._set_precision_items(capabilities.precisions, spec.argument, model_kind)
        is_sam2 = model_kind == "sam2" and spec.argument == "onnx"
        if is_sam2:
            self._set_line_edit(self.imgsz_edit, "1024")
            self._set_spin_value(self.batch_spin, 1)
        self.imgsz_box.setVisible(True)
        self.batch_box.setVisible(True)
        self.imgsz_edit.setEnabled(not is_sam2 and not self.is_exporting)
        self.batch_spin.setEnabled(
            capabilities.supports_batch and not is_sam2 and not self.is_exporting
        )
        self.conf_spin.setEnabled(capabilities.supports_nms and not self.is_exporting)
        self.iou_spin.setEnabled(capabilities.supports_nms and not self.is_exporting)
        self.max_det_spin.setEnabled(capabilities.supports_nms and not self.is_exporting)

        self.simplify_box.setVisible(
            "simplify" in option_keys and capabilities.supports_simplify
        )
        supports_opset = (
            "opset" in option_keys and capabilities.supports_opset and not is_sam2
        )
        supports_workspace = (
            "workspace" in option_keys and capabilities.supports_workspace
        )
        self.opset_box.setVisible(supports_opset)
        self.workspace_box.setVisible(supports_workspace)
        self.optimize_box.setVisible(
            "optimize" in option_keys and capabilities.supports_optimize
        )
        self.basic_format_box.setVisible(
            capabilities.supports_simplify or capabilities.supports_optimize
        )
        # A hidden simplify/optimize child can leave the shared wrapper with
        # the previous format's cached width. Refresh it before laying out the
        # OpenVINO/NMS/dynamic row so those controls return to the left edge.
        self.basic_format_box.updateGeometry()
        self.inference_format_box.setVisible(supports_opset or supports_workspace)
        has_basic_options = any(
            (
                capabilities.supports_simplify,
                capabilities.supports_optimize,
                "nms" in option_keys and capabilities.supports_nms,
                "dynamic" in option_keys and capabilities.supports_dynamic_batch,
            )
        )
        self.basic_options_box.setVisible(has_basic_options)

        has_dynamic = (
            ("dynamic" in option_keys or "dynamic_onnx" in option_keys)
            and (
            capabilities.supports_dynamic_batch
            or capabilities.supports_dynamic_height
            or capabilities.supports_dynamic_width
            )
        ) and not is_sam2
        self.dynamic_box.setVisible(is_onnx and has_dynamic)
        self.dynamic_input_check.setVisible(
            has_dynamic
            and "dynamic" in option_keys
            and not is_onnx
            and capabilities.supports_dynamic_batch
        )
        self.dynamic_batch_check.setVisible(False)
        self.dynamic_height_check.setVisible(False)
        self.dynamic_width_check.setVisible(False)
        onnx_dynamic_visible = (
            has_dynamic
            and "dynamic_onnx" in option_keys
            and is_onnx
            and capabilities.supports_dynamic_batch
        )
        self.onnx_dynamic_batch_check.setVisible(onnx_dynamic_visible)
        self.onnx_dynamic_size_check.setVisible(
            onnx_dynamic_visible
            and (
                capabilities.supports_dynamic_height
                or capabilities.supports_dynamic_width
            )
        )
        self.onnx_dynamic_batch_check.setEnabled(not self.is_exporting)
        self.onnx_dynamic_size_check.setEnabled(not self.is_exporting)
        self.dynamic_input_check.setEnabled(not self.is_exporting)

        self.nms_box.setVisible("nms" in option_keys and capabilities.supports_nms)
        self.agnostic_nms_check.setVisible(
            "nms" in option_keys and capabilities.supports_nms
        )
        self.nms_check.setEnabled(not self.is_exporting)
        self.agnostic_nms_check.setEnabled(not self.is_exporting)

        precision = {"FP16": "fp16", "INT8": "int8"}.get(
            self.precision_combo.currentText(), "fp32"
        )
        optimize_enabled = (
            capabilities.supports_optimize
            and precision != "fp16"
            and not self.is_exporting
        )
        if capabilities.supports_optimize and precision == "fp16" and self.optimize_check.isChecked():
            self.optimize_check.setChecked(False)
        self.optimize_check.setEnabled(optimize_enabled)
        int8_enabled = self.precision_combo.currentText() == "INT8"
        self.int8_box.setVisible(
            "int8" in option_keys
            and int8_enabled
            and capabilities.supports_calibration
        )
        self.validate_quantized_box.setVisible(
            int8_enabled and capabilities.supports_quantized_validation
        )
        self.validation_samples_box.setVisible(
            int8_enabled and capabilities.supports_quantized_validation
        )
        self.simplify_check.setEnabled(
            capabilities.supports_simplify and not self.is_exporting
        )
        QTimer.singleShot(0, self, self._reflow_layout)

    @staticmethod
    def _uses_unified_dynamic_input(export_format: str, model_kind: str | None = None) -> bool:
        return export_format != "onnx" and model_kind != "sam2"

    @staticmethod
    def _set_line_edit(edit, value: str) -> None:
        edit.blockSignals(True)
        edit.setText(value)
        edit.blockSignals(False)

    @staticmethod
    def _set_spin_value(spin, value) -> None:
        spin.blockSignals(True)
        spin.setValue(value)
        spin.blockSignals(False)

    def _set_precision_items(
        self,
        precisions: tuple[str, ...],
        export_format: str,
        model_kind: str,
    ):
        labels = {"fp32": "FP32", "fp16": "FP16", "int8": "INT8"}
        current = self.precision_combo.currentText()
        current_value = {value: key for key, value in labels.items()}.get(current, "fp32")
        self.precision_combo.blockSignals(True)
        self.precision_combo.clear()
        self.precision_combo.addItems([labels[item] for item in precisions])
        model = self.precision_combo.model()
        for index, precision in enumerate(precisions):
            item = model.item(index)
            if item is None:
                continue
            available = True
            if export_format == "torchscript" and precision == "fp16":
                available = self._runtime_capability_for(
                    export_format, model_kind, precision
                ).available
            item.setEnabled(available)
        selected_value = "fp32"
        if current_value in precisions:
            current_index = precisions.index(current_value)
            if model.item(current_index) is not None and model.item(current_index).isEnabled():
                self.precision_combo.setCurrentText(labels[current_value])
                selected_value = current_value
            else:
                self.precision_combo.setCurrentIndex(0)
                selected_value = precisions[0]
        else:
            self.precision_combo.setCurrentIndex(0)
            selected_value = precisions[0]
        self.precision_combo.blockSignals(False)
        if selected_value != current_value:
            self.update_setting("model_export", "precision", value=selected_value)

    def _current_model_kind(self) -> str:
        text = self.model_combo.currentText().strip()
        if not text:
            return "yolo"
        return model_kind_from_path(Path(self.model_path_from_text(text)))

    def _update_format_availability(self, model_kind: str) -> None:
        model = self.format_combo.model()
        for index in range(self.format_combo.count()):
            item = model.item(index)
            if item is None:
                continue
            spec = resolve_export_format(self.format_combo.itemText(index))
            enabled = model_kind != "sam2" or spec.argument == "onnx"
            if enabled and spec.argument == "engine":
                capability = self._runtime_capability_for(
                    spec.argument, model_kind, "fp32"
                )
                enabled = capability.available or not any(
                    marker in capability.reason for marker in ("GPU", "CPU 版")
                )
            item.setEnabled(enabled)

    def preview_export(self):
        try:
            config = self.collect_config()
        except ValueError as exc:
            QMessageBox.warning(self, "无法预览", str(exc))
            return
        spec = resolve_export_format(config.export_format)
        capability = self._runtime_capability(spec.argument, config.precision)
        target = export_artifact_path(
            config.model_path,
            config.output_dir,
            spec.argument,
            config.precision,
        )
        overwrite = "是，执行前会要求确认" if target.exists() else "否"
        self.log.setPlainText(
            "\n".join(
                [
                    f"源模型：{config.model_path}",
                    f"目标格式：{spec.display_name}",
                    f"模型类型：{self._current_model_kind().upper()}",
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

    def start_export(self):
        if self.is_exporting:
            return
        try:
            config = self.collect_config()
        except ValueError as exc:
            QMessageBox.warning(self, "无法转换", str(exc))
            return
        capability = self._runtime_capability(config.export_format, config.precision)
        if not capability.available:
            QMessageBox.warning(self, "转换环境不可用", capability.reason)
            return
        target = export_artifact_path(
            config.model_path,
            config.output_dir,
            config.export_format,
            config.precision,
        )
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
            self.precision_combo,
            self.imgsz_edit,
            self.batch_spin,
            self.dynamic_box,
            self.nms_box,
            self.int8_box,
            self.opset_box,
            self.workspace_box,
            self.optimize_box,
            self.dynamic_input_check,
            self.calibration_pack_btn,
            self.onnx_simplify_btn,
            self.onnx_nms_btn,
            self.onnx_agnostic_btn,
            self.onnx_dynamic_batch_check,
            self.onnx_dynamic_size_check,
            self.onnx_conf_spin,
            self.onnx_iou_spin,
            self.onnx_max_det_spin,
            self.onnx_opset_spin,
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

    def _runtime_capability(self, export_format: str, precision: str):
        return self._runtime_capability_for(
            export_format, self._current_model_kind(), precision
        )

    def _runtime_capability_for(
        self, export_format: str, model_kind: str, precision: str
    ):
        try:
            return export_capability(
                export_format,
                model_kind=model_kind,
                precision=precision,
            )
        except TypeError:
            return export_capability(export_format)
