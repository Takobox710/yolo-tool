from __future__ import annotations

from pathlib import Path

from src.shared.qt import QMessageBox


class AiPrelabelRuntimeMixin:

    def fail_ai_labeling(self, message: str) -> None:
        if not self.page.context.tasks.is_current(self._ai_lease):
            return
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.undo_btn.setEnabled(bool(self.backups))
        self.stop_event.clear()
        self.page.context.tasks.finish(self._ai_lease)
        self._ai_lease = None
        self.append_log(f"失败：{message}")
        QMessageBox.warning(self, "AI 预标注", message)


    def stop_ai_labeling(self) -> None:
        self.stop_event.set()
        self.stop_btn.setEnabled(False)
        self.runtime_worker.request_stop()
        self.append_log("已请求停止 AI 预标注")


    def undo_ai_changes(self) -> None:
        if not self.backups:
            return
        for image_path, (json_text, yolo_text) in self.backups.items():
            json_path = self.page.path_from_setting("annotations_dir") / f"{image_path.stem}.json"
            yolo_path = self.page.path_from_setting("labels_dir") / f"{image_path.stem}.txt"
            if json_text is None:
                if json_path.exists():
                    json_path.unlink()
            else:
                json_path.write_text(json_text, encoding="utf-8")
            if yolo_text is None:
                if yolo_path.exists():
                    yolo_path.unlink()
            else:
                yolo_path.write_text(yolo_text, encoding="utf-8")
        self.page.context.settings.dataset.class_names = list(self.original_class_names)
        self.page.save_settings()
        self.page._refresh_class_state()
        self.page.refresh_file_list()
        if self.page.current_index >= 0:
            self.page.load_current()
        self.append_log("已恢复本次 AI 预标注前的标注文件")
        self.undo_btn.setEnabled(False)

    def apply_progress(self, payload: dict) -> None:
        total = max(1, int(payload.get("total") or 1))
        index = int(payload.get("index") or 0)
        self.progress_bar.setValue(int(index * 100 / total))
        if payload.get("type") == "log":
            self.append_log(str(payload.get("message") or ""))
            return
        image_name = str(payload.get("image_name") or "")
        result_count = int(payload.get("result_count") or 0)
        self.append_log(f"{index}/{total} {image_name} -> 新增 {result_count} 个标注")
        stats = dict(payload.get("sam3_stats") or {})
        if stats:
            self.append_log(
                f"  SAM 3 候选 {stats.get('raw_count', 0)}，"
                f"面积过滤 {stats.get('area_filtered', 0)}，"
                f"重叠去重 {stats.get('overlap_filtered', 0)}"
            )


    def finish_ai_labeling(self, result) -> None:
        if not self.page.context.tasks.is_current(self._ai_lease):
            return
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        if self.stop_event.is_set():
            self.undo_btn.setEnabled(bool(self.backups))
            self.progress_bar.setValue(0)
            self.append_log("AI 预标注已停止")
            self.stop_event.clear()
            self.page.context.tasks.finish(self._ai_lease)
            self._ai_lease = None
            return
        self.undo_btn.setEnabled(bool(self.backups))
        self.progress_bar.setValue(100 if result.total else 0)
        self.append_log(f"完成：已处理 {result.processed}/{result.total} 张图片")
        self.page.refresh_file_list()
        if self.page.current_index >= 0:
            self.page.load_current()
        self.page.context.tasks.finish(self._ai_lease)
        self._ai_lease = None


    def start_ai_labeling(self) -> None:
        if not self.start_btn.isEnabled():
            return
        if self.page.context.tasks.is_active("ai_label"):
            QMessageBox.information(self, "AI 预标注", "已有 AI 预标注任务正在运行。")
            return
        model_path = self.resolved_model_path()
        if not model_path:
            QMessageBox.warning(self, "AI 预标注", "请先选择模型文件。")
            return
        targets = self.resolved_target_images()
        if self.current_range_mode() == "自定义图片" and not targets:
            QMessageBox.information(self, "AI 预标注", "请先在图片列表中勾选至少一张图片。")
            return
        if not targets:
            QMessageBox.information(self, "AI 预标注", "当前没有可处理的图片。")
            return
        self._capture_backend_values()
        sam3_prompts, sam3_enabled = self.collect_sam3_prompts()
        if self.active_backend == "sam3":
            valid_prompts = [
                name for name in sam3_enabled if sam3_prompts.get(name, "").strip()
            ]
            if not valid_prompts:
                QMessageBox.warning(self, "AI 预标注", "请至少启用一个带文本提示词的项目类别。")
                return
            mapping = {}
        else:
            mapping = self.collect_mapping()
            if not mapping:
                QMessageBox.warning(self, "AI 预标注", "请至少匹配一个模型类别到标注类别。")
                return
        self.page.sam_assist.release_for_ai_prelabel()
        self._snapshot_targets(targets)
        self.original_class_names = list(self.page.class_names())
        self.progress_bar.setValue(0)
        self.progress_log.clear()
        if self.active_backend == "sam3":
            self.append_log(f"已启用 {len(valid_prompts)} 个 SAM 3 文本提示词")
        else:
            self.append_log(f"已加载 {len(self.model_labels)} 个模型类别")
        self.stop_event.clear()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.undo_btn.setEnabled(False)
        self._ai_lease = self.page.context.tasks.begin(
            "ai_label",
            generation=self.page.context.generation,
            stop=self.runtime_worker.request_stop,
        )
        if self._ai_lease is None:
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            return
        worker_kwargs = {
            "image_items": [str(path) for path in self.page.image_items],
            "target_images": [str(path) for path in targets],
            "current_image": (
                str(self.page.current_image_path)
                if self.page.current_image_path is not None
                else ""
            ),
            "annotations_dir": str(self.page.path_from_setting("annotations_dir")),
            "labels_dir": str(self.page.path_from_setting("labels_dir")),
            "model_path": model_path,
            "backend": self.active_backend,
            "confidence": float(self.conf_spin.value()),
            "iou": float(self.iou_spin.value()),
            "imgsz": max(640, int(self.page.canvas.image_size[0] or 640)),
            "range_mode": self.current_range_mode(),
            "current_index": self.page.current_index,
            "selected_images": [str(path) for path in self.custom_selected_images],
            "process_mode": self.current_process_mode(),
            "class_mapping": mapping,
            "class_names": list(self.page.class_names()),
            "sam3_prompts": sam3_prompts,
            "sam3_enabled_classes": sam3_enabled,
            "sam3_output_shape": self.saved_sam3_output_shape,
            "sam3_min_area": self.saved_sam3_min_area,
            "sam3_polygon_simplify_ratio": self.saved_sam3_polygon_simplify_ratio,
            "line_expand_pixels": self.page.context.settings.annotation.line_expand_pixels,
            "output_mode": self.page.output_mode,
            "auto_convert_yolo": bool(self.page.context.settings.annotation.auto_convert_yolo),
        }
        self._ensure_runtime_worker_started()
        self.runtime_worker.start_ai_labeling(worker_kwargs)


__all__ = ['AiPrelabelRuntimeMixin']
