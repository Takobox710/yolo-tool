from __future__ import annotations

from pathlib import Path

from src.services.annotation import (
    available_ai_models,
    resolve_ai_model_path,
)
from src.services.annotation.sam3_text import (
    find_sam3_model_paths,
    is_sam3_checkpoint,
)
from src.services.data_ops import simplified_model_path
from src.services.validation import find_result_model_paths
from src.shared.qt import QMessageBox, Qt
from src.ui.features.annotation.ai.mapping import (
    collect_mapping as collect_ai_mapping,
    configure_mapping_table,
    configure_sam3_prompt_table,
    populate_mapping_table as populate_ai_mapping_table,
    populate_sam3_prompt_table,
    update_mapping_status as update_ai_mapping_status,
    update_sam3_prompt_status,
)


class AiPrelabelMappingMixin:

    def collect_sam3_prompts(self) -> tuple[dict[str, str], list[str]]:
        prompts: dict[str, str] = {}
        enabled: list[str] = []
        for name, check, edit in zip(
            self.sam3_class_names,
            self.sam3_checks,
            self.sam3_prompt_edits,
        ):
            prompts[name] = edit.text().strip()
            if check.isChecked():
                enabled.append(name)
        return prompts, enabled


    def populate_mapping_table(self) -> None:
        self.mapping_combos = populate_ai_mapping_table(
            table=self.mapping_table,
            summary=self.mapping_summary,
            model_labels=self.model_labels,
            class_names=self.page.class_names(),
            status_changed=self.update_mapping_status,
        )


    def _ensure_runtime_worker_started(self) -> None:
        if not self.runtime_worker.isRunning():
            self.runtime_worker.start()


    def reload_model_labels(self) -> None:
        model_path = self.resolved_model_path()
        self._pending_labels_model_path = model_path
        self.model_labels = []
        backend = "sam3" if is_sam3_checkpoint(model_path) else "yolo"
        self._set_backend_controls(backend)
        self.mapping_table.setRowCount(0)
        if not model_path:
            self.mapping_summary.setText("未选择模型")
            return
        if backend == "sam3":
            self.mapping_summary.setText("正在准备 SAM 3 文本提示词")
            self.populate_sam3_prompts()
            return
        configure_mapping_table(self.mapping_table)
        model_file = Path(model_path)
        if not model_file.exists() or model_file.stat().st_size < 1024:
            self.mapping_summary.setText("模型类别待加载")
            return
        self._ensure_runtime_worker_started()
        self.runtime_worker.request_model_labels(model_path)


    def update_sam3_prompt_status(self, *_args) -> None:
        update_sam3_prompt_status(
            self.mapping_table,
            self.mapping_summary,
            self.sam3_checks,
            self.sam3_prompt_edits,
        )


    def _on_sam3_shape_changed(self, *_args) -> None:
        if self.active_backend == "sam3":
            self.saved_sam3_output_shape = str(self.shape_combo.currentData() or "rect")


    def _shutdown_runtime_worker(self) -> None:
        if self.runtime_worker.isRunning():
            self.runtime_worker.shutdown()
            self.runtime_worker.wait(3000)
        self._pending_labels_model_path = ""


    def collect_mapping(self) -> dict[str, str]:
        return collect_ai_mapping(self.mapping_table, self.mapping_combos)


    def append_log(self, text: str) -> None:
        self.progress_log.append(text)


    def _toggle_sam3_advanced(self, expanded: bool) -> None:
        self.sam3_advanced_toggle.setArrowType(
            Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow
        )
        self.sam3_advanced_frame.setVisible(bool(expanded and self.active_backend == "sam3"))


    def update_target_count(self) -> None:
        targets = self.resolved_target_images()
        if self.current_range_mode() == "自定义图片":
            self.range_list_btn.setText("列表")
            self.range_list_btn.setToolTip(f"当前已选择 {len(targets)} 张图片")
            return
        self.range_count_label.setText(f"已选择 {len(targets)} 张图片")


    def populate_sam3_prompts(self) -> None:
        self.sam3_class_names = list(self.page.class_names())
        configure_sam3_prompt_table(self.mapping_table)
        self.sam3_checks, self.sam3_prompt_edits = populate_sam3_prompt_table(
            table=self.mapping_table,
            summary=self.mapping_summary,
            class_names=self.sam3_class_names,
            saved_prompts=self.saved_sam3_prompts,
            saved_enabled_classes=self.saved_sam3_enabled_classes,
        )
        for check, edit in zip(self.sam3_checks, self.sam3_prompt_edits):
            check.stateChanged.connect(self.update_sam3_prompt_status)
            edit.textChanged.connect(self.update_sam3_prompt_status)


    def _set_backend_controls(self, backend: str) -> None:
        backend = "sam3" if backend == "sam3" else "yolo"
        if backend == self.active_backend:
            if backend == "sam3" and self.sam3_class_names == []:
                self._on_sam3_shape_changed()
            return
        self._capture_backend_values()
        self.active_backend = backend
        if backend == "sam3":
            self.conf_spin.setValue(self.saved_sam3_confidence)
            self.iou_spin.setValue(self.saved_sam3_dedup_iou)
            index = self.shape_combo.findData(self.saved_sam3_output_shape)
            self.shape_combo.setCurrentIndex(max(0, index))
            self.sam3_min_area_spin.setValue(self.saved_sam3_min_area)
            self.sam3_simplify_spin.setValue(self.saved_sam3_polygon_simplify_ratio * 100.0)
            self.conf_spin.setToolTip("SAM 3 概念分割置信度阈值")
            self.iou_spin.setToolTip("不同文本类别结果的 mask 去重阈值")
            self.threshold_widget.setVisible(False)
            self.shape_label.setVisible(True)
            self.shape_combo.setVisible(True)
            self.sam3_advanced_toggle.setVisible(True)
            self.shape_label.setText("标注形状:")
        else:
            self.conf_spin.setValue(self.saved_confidence)
            self.iou_spin.setValue(self.saved_iou)
            self.conf_spin.setToolTip("YOLO 置信度阈值")
            self.iou_spin.setToolTip("YOLO NMS IoU 阈值")
            self.threshold_widget.setVisible(True)
            self.sam3_advanced_toggle.setVisible(False)
            self.sam3_advanced_frame.setVisible(False)
            self.shape_label.setVisible(False)
            self.shape_combo.setVisible(False)


    def update_mapping_status(self) -> None:
        update_ai_mapping_status(
            table=self.mapping_table,
            summary=self.mapping_summary,
            model_labels=self.model_labels,
            mapping_combos=self.mapping_combos,
        )


    def _snapshot_targets(self, targets: list[Path]) -> None:
        self.backups = {}
        for image_path in targets:
            json_path = self.page.path_from_setting("annotations_dir") / f"{image_path.stem}.json"
            yolo_path = self.page.path_from_setting("labels_dir") / f"{image_path.stem}.txt"
            json_text = json_path.read_text(encoding="utf-8") if json_path.exists() else None
            yolo_text = yolo_path.read_text(encoding="utf-8") if yolo_path.exists() else None
            self.backups[image_path] = (json_text, yolo_text)


    def apply_model_labels_error(self, model_path: str, message: str) -> None:
        if str(model_path) != self.resolved_model_path():
            return
        self.mapping_summary.setText(f"加载模型类别失败：{message}")


    def _capture_backend_values(self) -> None:
        if self.active_backend == "sam3":
            self.saved_sam3_confidence = float(self.conf_spin.value())
            self.saved_sam3_dedup_iou = float(self.iou_spin.value())
            self.saved_sam3_output_shape = str(self.shape_combo.currentData() or "rect")
            self.saved_sam3_min_area = int(self.sam3_min_area_spin.value())
            self.saved_sam3_polygon_simplify_ratio = self.sam3_simplify_spin.value() / 100.0
        else:
            self.saved_confidence = float(self.conf_spin.value())
            self.saved_iou = float(self.iou_spin.value())


    def apply_model_labels(self, model_path: str, labels: list[str]) -> None:
        if str(model_path) != self.resolved_model_path():
            return
        self.model_labels = list(labels)
        self.populate_mapping_table()


__all__ = ['AiPrelabelMappingMixin']
