from __future__ import annotations

from scr.services.resize_service import ResizeConfig, preview_resize, run_resize
from scr.ui.page_base import BasePage
from scr.ui.qt import QGridLayout, QHBoxLayout, QPushButton, QTextEdit, QVBoxLayout

class ResizeTab(BasePage):
    def __init__(self, app):
        super().__init__(app)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        resize = app.settings["image_resize"]
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        self.source_box, self.source_edit = self.path_field(
            "图片目录",
            app.settings["paths"]["images_dir"],
            self.choose_dir,
            "选择待压缩的图片目录",
        )
        self.backup_box, self.backup_edit = self.path_field(
            "备份目录",
            resize["backup_dir"],
            self.choose_dir,
            "选择原图备份目录",
        )
        self.output_box, self.output_edit = self.path_field(
            "输出目录",
            resize["output_dir"],
            self.choose_dir,
            "选择压缩结果输出目录",
        )
        self.canvas_box, self.canvas_edit = self.field(
            "画布尺寸",
            str(resize["canvas_size"]),
            placeholder="例如 960",
        )
        self.bg_box, self.bg_combo = self.combo_field(
            "背景颜色",
            resize["background"],
            ["white", "black"],
        )
        self.output_mode_box, self.output_mode_combo = self.combo_field(
            "输出方式",
            app.settings.get("features", {}).get(
                "resize_output_mode", "输出到新文件夹"
            ),
            ["输出到新文件夹", "覆盖原文件"],
        )
        for index, widget in enumerate(
            [
                self.source_box,
                self.backup_box,
                self.output_box,
                self.canvas_box,
                self.output_mode_box,
                self.bg_box,
            ]
        ):
            grid.addWidget(widget, index // 3, index % 3)
        backup_toggle_box, self.backup_check = self.checkbox_with_help(
            "备份原始图片",
            bool(resize.get("backup_enabled", False)),
        )
        grid.addWidget(backup_toggle_box, 2, 0)
        layout.addLayout(grid)
        actions = QHBoxLayout()
        preview_button = QPushButton("预览压缩")
        preview_button.clicked.connect(self.preview)
        run_button = QPushButton("执行压缩")
        run_button.clicked.connect(self.run)
        actions.addWidget(preview_button)
        actions.addWidget(run_button)
        actions.addStretch(1)
        layout.addLayout(actions)
        self.log = QTextEdit()
        self.prepare_readonly_text(self.log)
        layout.addWidget(self.log, 1)
        self._connect_persistence()

    def config(self):
        return ResizeConfig(
            source_dir=self.path_from_edit(self.source_edit),
            output_dir=self.path_from_edit(self.output_edit),
            backup_dir=self.path_from_edit(self.backup_edit),
            canvas_size=int(self.canvas_edit.text()),
            background=self.bg_combo.currentText(),
            backup_enabled=self.backup_check.isChecked(),
        )

    def preview(self):
        result = preview_resize(self.config())
        self.log.setPlainText(
            f"计划处理 {len(result.items)} 张图片\n输出方式: {self.output_mode_combo.currentText()}\n"
        )
        source_root = self.path_from_edit(self.source_edit)
        for item in result.items[:80]:
            self.log.append(
                f"{item.source.relative_to(source_root)}: {item.original_size} -> {item.resized_size}, scale={item.scale:.3f}"
            )

    def run(self):
        result = run_resize(self.config())
        self.log.append(
            f"\n压缩完成: {result.processed_count} 张，输出目录: {result.output_dir}"
        )

    def _connect_persistence(self):
        self.source_edit.textChanged.connect(
            lambda _text: self.update_setting(
                "paths", "images_dir", value=self.resolve_path_text(self.source_edit)
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
        self.canvas_edit.textChanged.connect(self._persist_canvas_size)
        self.bg_combo.currentTextChanged.connect(
            lambda value: self.update_setting("image_resize", "background", value=value)
        )
        self.output_mode_combo.currentTextChanged.connect(
            lambda value: self.update_setting(
                "features", "resize_output_mode", value=value
            )
        )

    def _persist_canvas_size(self, text: str):
        try:
            value = int(text)
        except ValueError:
            return
        self.update_setting("image_resize", "canvas_size", value=value)
