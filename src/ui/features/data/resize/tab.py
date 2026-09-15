from __future__ import annotations

import os
from pathlib import Path

from src.services.data_ops import (
    RESIZE_MODE_CANVAS,
    RESIZE_MODE_CROP,
    ResizeConfig,
    preview_resize,
    run_resize,
)
from src.ui.shared.page_base import BasePage
from src.shared.qt import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

class ResizeTab(BasePage):
    def __init__(self, context):
        super().__init__(context)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        resize = context.settings.image_resize
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        self.source_box, self.source_edit = self.path_field(
            "图片目录",
            resize.source_dir,
            self.choose_dir,
            "选择待压缩的图片目录",
        )
        self.backup_box, self.backup_edit = self.path_field(
            "备份目录",
            resize.backup_dir,
            self.choose_dir,
            "选择原图备份目录",
        )
        self.output_box, self.output_edit = self.path_field(
            "输出目录",
            resize.output_dir,
            self.choose_dir,
            "选择压缩结果输出目录",
        )
        self.mode_box, self.mode_combo = self.combo_field(
            "处理方式",
            resize.mode,
            [RESIZE_MODE_CANVAS, RESIZE_MODE_CROP],
        )
        self.ratio_box, self.ratio_combo = self.combo_field(
            "图片比例",
            resize.aspect_ratio,
            ["1:1", "4:3", "16:9", "3:4", "9:16"],
        )
        self.size_box, self.size_edit = self.field(
            "画布尺寸",
            resize.resolution,
            placeholder="例如 640×480",
        )
        self.bg_box, self.bg_combo = self.combo_field(
            "背景颜色",
            resize.background,
            ["white", "black"],
        )
        self.output_mode_box, self.output_mode_combo = self.combo_field(
            "输出方式",
            context.settings.features.resize_output_mode,
            ["输出到新文件夹", "覆盖原文件"],
        )
        for index, widget in enumerate(
            [
                self.source_box,
                self.backup_box,
                self.output_box,
                self.mode_box,
                self.ratio_box,
                self.size_box,
                self.output_mode_box,
                self.bg_box,
            ]
        ):
            grid.addWidget(widget, index // 3, index % 3)
        backup_toggle_box, self.backup_check = self.checkbox_with_help(
            "备份原始图片",
            resize.backup_enabled,
        )
        grid.addWidget(backup_toggle_box, 3, 0)
        layout.addLayout(grid)
        actions = QHBoxLayout()
        preview_button = QPushButton("预览压缩")
        preview_button.clicked.connect(self.preview)
        run_button = QPushButton("执行压缩")
        run_button.clicked.connect(self.run)
        self.open_output_btn = QPushButton("打开结果文件夹")
        self.open_output_btn.clicked.connect(self.open_output_dir)
        actions.addWidget(preview_button)
        actions.addWidget(run_button)
        actions.addWidget(self.open_output_btn)
        actions.addStretch(1)
        layout.addLayout(actions)
        self.log = QTextEdit()
        self.prepare_readonly_text(self.log)
        layout.addWidget(self.log, 1)
        self._connect_persistence()
        self._sync_mode_controls()

    def on_setting_changed(self, keys, value):
        if keys != ("image_resize", "source_dir"):
            return
        self.source_edit.blockSignals(True)
        self.source_edit.setText(self.display_path(value))
        self.source_edit.blockSignals(False)

    def config(self):
        return ResizeConfig(
            source_dir=self.path_from_edit(self.source_edit),
            output_dir=self.path_from_edit(self.output_edit),
            backup_dir=self.path_from_edit(self.backup_edit),
            canvas_size=resize_value(self.size_edit.text()),
            mode=self.mode_combo.currentText(),
            aspect_ratio=self.ratio_combo.currentText(),
            resolution=self.size_edit.text(),
            background=self.bg_combo.currentText(),
            backup_enabled=self.backup_check.isChecked(),
        )

    def preview(self):
        try:
            result = preview_resize(self.config())
        except ValueError as exc:
            self.log.setPlainText(f"无法预览：{exc}")
            return
        self.log.setPlainText(
            f"计划处理 {len(result.items)} 张图片\n处理方式: {self.mode_combo.currentText()}\n"
            f"图片比例: {self.ratio_combo.currentText()}\n输出方式: {self.output_mode_combo.currentText()}\n"
        )
        source_root = self.path_from_edit(self.source_edit)
        for item in result.items[:80]:
            detail = (
                f"{item.source.relative_to(source_root)}: {item.original_size} -> "
                f"{item.output_size}, scale={item.scale:.3f}"
            )
            if item.crop_box:
                detail += f", 裁剪区域={item.crop_box}"
            self.log.append(detail)

    def run(self):
        try:
            result = run_resize(self.config())
        except ValueError as exc:
            self.log.append(f"压缩失败：{exc}")
            return
        self.log.append(
            f"\n压缩完成: {result.processed_count} 张，输出目录: {result.output_dir}"
        )

    def open_output_dir(self):
        output_dir = Path(self.resolve_path_text(self.output_edit))
        output_dir.mkdir(parents=True, exist_ok=True)
        os.startfile(output_dir)

    def _connect_persistence(self):
        self.source_edit.textChanged.connect(
            lambda _text: self.update_setting(
                "image_resize", "source_dir", value=self.resolve_path_text(self.source_edit)
            )
        )
        self.backup_edit.textChanged.connect(
            lambda _text: self.update_setting(
                "image_resize",
                "backup_dir",
                value=self.resolve_path_text(self.backup_edit),
            )
        )
        self.output_edit.textChanged.connect(
            lambda _text: self.update_setting(
                "image_resize",
                "output_dir",
                value=self.resolve_path_text(self.output_edit),
            )
        )
        self.backup_check.toggled.connect(
            lambda checked: self.update_setting(
                "image_resize", "backup_enabled", value=bool(checked)
            )
        )
        self.mode_combo.currentTextChanged.connect(self._set_resize_mode)
        self.ratio_combo.currentTextChanged.connect(self._set_aspect_ratio)
        self.size_edit.textChanged.connect(self._persist_resolution)
        self.bg_combo.currentTextChanged.connect(
            lambda value: self.update_setting("image_resize", "background", value=value)
        )
        self.output_mode_combo.currentTextChanged.connect(
            lambda value: self.update_setting(
                "features", "resize_output_mode", value=value
            )
        )

    def _set_resize_mode(self, value: str):
        self.update_setting("image_resize", "mode", value=value)
        self._sync_mode_controls()

    def _set_aspect_ratio(self, value: str):
        self.update_setting("image_resize", "aspect_ratio", value=value)

    def _persist_resolution(self, text: str):
        try:
            value = resize_value(text)
        except ValueError:
            return
        self.update_setting("image_resize", "resolution", value=text)
        self.update_setting("image_resize", "canvas_size", value=value)

    def _sync_mode_controls(self):
        is_canvas = self.mode_combo.currentText() == RESIZE_MODE_CANVAS
        label = self.size_box.findChild(QLabel, "fieldLabel")
        if label is not None:
            self._set_help_target(
                label,
                "画布尺寸" if is_canvas else "输出分辨率",
                "画布压缩使用该尺寸创建补边画布；裁剪模式使用该尺寸输出裁剪结果。",
            )
        self.bg_box.setEnabled(is_canvas)


def resize_value(text: str) -> int:
    normalized = str(text).strip().lower().replace("×", "x")
    width, separator, height = normalized.partition("x")
    if not separator:
        return int(width)
    return max(int(width), int(height))
