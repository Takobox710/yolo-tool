from __future__ import annotations

from pathlib import Path

from src.services.annotation import available_ai_models, collect_ai_target_images, resolve_ai_model_path
from src.services.data_ops import simplified_model_path
from src.services.validation import find_result_model_paths
from src.services.annotation.sam3_text import find_sam3_model_paths, is_sam3_checkpoint
from src.shared.qt import QDialog, QFileDialog, QMessageBox
from src.ui.features.annotation.ai.image_selection_dialog import CustomAiImageSelectionDialog
from src.ui.features.annotation.ai.preferences import (
    ai_prelabel_settings,
    load_ai_prelabel_preferences,
    preferred_ai_model_text,
    save_ai_prelabel_preferences,
)


class AiPrelabelStateMixin:

    def open_custom_image_list(self) -> None:
        if not self.page.image_items:
            QMessageBox.information(self, "AI 预标注", "当前图片文件夹没有可选择的图片。")
            return
        dialog = CustomAiImageSelectionDialog(
            self.page.image_items,
            self.custom_selected_images,
            self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.custom_selected_images = dialog.selected_image_paths()
            self.update_target_count()


    def resolved_target_images(self) -> list[Path]:
        return collect_ai_target_images(
            self.page.image_items,
            self.page.current_image_path,
            self.page.path_from_setting("annotations_dir"),
            self.page.path_from_setting("labels_dir"),
            self.current_range_mode(),
            current_index=self.page.current_index,
            selected_images=self.custom_selected_images,
        )


    def choose_model(self) -> None:
        models_dir = self.page.project_root() / "data" / "models"
        models_dir.mkdir(parents=True, exist_ok=True)
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择模型文件",
            str(models_dir),
            "PyTorch 模型 (*.pt);;所有文件 (*)",
        )
        if path:
            display_name = (
                Path(path).name if is_sam3_checkpoint(path) else self.page.display_path(path)
            )
            self.model_combo.setCurrentText(display_name)


    def current_process_mode(self) -> str:
        return "替换" if self.replace_radio.isChecked() else "追加"


    def _ai_prelabel_settings(self) -> dict:
        return ai_prelabel_settings(self.page)


    def _load_saved_preferences(self) -> None:
        preferences = load_ai_prelabel_preferences(self.page)
        self.saved_model_path = str(preferences["model_path"])
        self.saved_confidence = float(preferences["confidence"])
        self.saved_iou = float(preferences["iou"])
        self.saved_sam3_confidence = float(preferences["sam3_confidence"])
        self.saved_sam3_dedup_iou = float(preferences["sam3_dedup_iou"])
        self.saved_sam3_output_shape = str(preferences["sam3_output_shape"])
        self.saved_sam3_prompts = dict(preferences["sam3_prompts"])
        self.saved_sam3_enabled_classes = list(preferences["sam3_enabled_classes"])
        if not self.saved_sam3_prompts and not self.saved_sam3_enabled_classes:
            if str(self.page.output_mode).strip() == "obb":
                self.saved_sam3_output_shape = "obb"
            elif str(self.page.output_mode).strip() == "seg":
                self.saved_sam3_output_shape = "polygon"
        self.saved_sam3_min_area = int(preferences["sam3_min_area"])
        self.saved_sam3_polygon_simplify_ratio = float(
            preferences["sam3_polygon_simplify_ratio"]
        )
        self.saved_range_mode = str(preferences["range_mode"])
        self.saved_process_mode = str(preferences["process_mode"])
        self.custom_selected_images = list(preferences["custom_selected_images"])


    def on_range_mode_changed(self, _text: str = "") -> None:
        is_custom = self.current_range_mode() == "自定义图片"
        self.range_count_label.setHidden(is_custom)
        self.range_list_btn.setHidden(not is_custom)
        self.range_list_btn.setText("列表")
        self.update_target_count()


    def refresh_model_choices(self, preferred_model: str = "") -> None:
        project_root = self.page.project_root()
        result_dir = Path(self.page.context.settings.paths.result_dir)
        self._model_display_paths = {}
        display_names: list[str] = []
        seen: set[str] = set()

        for path in find_result_model_paths(
            result_dir, show_last_training_models=False
        ):
            resolved_path = path.resolve()
            resolved_text = str(resolved_path)
            if resolved_text in seen:
                continue
            display_name = simplified_model_path(str(resolved_path), project_root)
            self._model_display_paths[display_name] = resolved_path
            display_names.append(display_name)
            seen.add(resolved_text)

        for path in find_sam3_model_paths(project_root):
            resolved_path = path.resolve()
            resolved_text = str(resolved_path)
            if resolved_text in seen:
                continue
            display_name = resolved_path.name
            self._model_display_paths[display_name] = resolved_path
            display_names.append(display_name)
            seen.add(resolved_text)

        for model_name in available_ai_models(project_root):
            resolved_text = resolve_ai_model_path(model_name, project_root)
            if resolved_text in seen:
                continue
            if Path(resolved_text).name.lower().startswith("sam2"):
                continue
            display_names.append(model_name)
            if resolved_text:
                self._model_display_paths[model_name] = Path(resolved_text)
                seen.add(resolved_text)

        selected_text = ""
        preferred_text = str(preferred_model or "").strip()
        if preferred_text:
            preferred_path = Path(resolve_ai_model_path(preferred_text, project_root))
            for display_name, resolved_path in self._model_display_paths.items():
                if resolved_path == preferred_path:
                    selected_text = display_name
                    break
            else:
                selected_text = preferred_path.name if preferred_path.name else preferred_text

        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        self.model_combo.addItems(display_names)
        if selected_text:
            self.model_combo.setCurrentText(selected_text)
        self.model_combo.blockSignals(False)


    def reject(self) -> None:
        self._save_preferences()
        self._shutdown_runtime_worker()
        super().reject()


    def showEvent(self, event):  # noqa: N802 - Qt API name
        super().showEvent(event)
        if not self.model_labels:
            self.reload_model_labels()


    def resolved_model_path(self) -> str:
        text = self.model_combo.currentText().strip()
        mapped = self._model_display_paths.get(text)
        if mapped is not None:
            return str(mapped)
        return resolve_ai_model_path(text, self.page.project_root())


    def closeEvent(self, event):  # noqa: N802 - Qt API name
        self._save_preferences()
        self._shutdown_runtime_worker()
        super().closeEvent(event)


    def current_range_mode(self) -> str:
        return self.range_combo.currentText() or "当前图片"


    def accept(self) -> None:
        self._save_preferences()
        self._shutdown_runtime_worker()
        super().accept()


    def _preferred_model_text(self) -> str:
        return preferred_ai_model_text(self.page, self.saved_model_path)


    def _save_preferences(self) -> None:
        self._capture_backend_values()
        prompts, enabled = self.collect_sam3_prompts()
        save_ai_prelabel_preferences(
            self.page,
            model_path=self.resolved_model_path(),
            fallback_model_text=self.model_combo.currentText().strip(),
            confidence=self.saved_confidence,
            iou=self.saved_iou,
            sam3_confidence=self.saved_sam3_confidence,
            sam3_dedup_iou=self.saved_sam3_dedup_iou,
            sam3_output_shape=self.saved_sam3_output_shape,
            sam3_prompts=prompts,
            sam3_enabled_classes=enabled,
            sam3_min_area=self.saved_sam3_min_area,
            sam3_polygon_simplify_ratio=self.saved_sam3_polygon_simplify_ratio,
            range_mode=self.current_range_mode(),
            process_mode=self.current_process_mode(),
            custom_selected_images=self.custom_selected_images,
        )


__all__ = ['AiPrelabelStateMixin']
