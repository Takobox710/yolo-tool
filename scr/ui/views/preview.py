from __future__ import annotations

from pathlib import Path

from PIL import Image

from scr.services.annotation_service import load_yolo_annotations, render_annotation_preview
from scr.services.rename_service import natural_sort_key
from scr.ui.page_base import BasePage, ImageView, _IMAGE_SUFFIXES
from scr.ui.qt import QDialog, QDialogButtonBox, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QMessageBox, QPushButton, QVBoxLayout

class PreviewTab(BasePage):
    def __init__(self, app):
        super().__init__(app)
        self.preview_items: list[Path] = []
        self.preview_index = 0
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        grid = QGridLayout()
        self.image_box, self.image_edit = self.path_field(
            "图片文件夹", app.settings["paths"]["images_dir"], self.choose_dir
        )
        self.label_box, self.label_edit = self.path_field(
            "标注文件夹", app.settings["paths"]["labels_dir"], self.choose_dir
        )
        grid.addWidget(self.image_box, 0, 0)
        grid.addWidget(self.label_box, 0, 1)
        layout.addLayout(grid)
        actions = QHBoxLayout()
        for text, slot in [
            ("扫描", self.load_preview_items),
            ("上一张", self.prev_image),
            ("下一张", self.next_image),
            ("列表", self.show_preview_list),
        ]:
            button = QPushButton(text)
            button.clicked.connect(slot)
            actions.addWidget(button)
        self.current_label = QLabel("等待扫描图片")
        actions.addWidget(self.current_label, 1)
        layout.addLayout(actions)
        images = QHBoxLayout()
        self.source_view = ImageView("原始图片")
        self.result_view = ImageView("标注预览")
        images.addWidget(self.source_view)
        images.addWidget(self.result_view)
        layout.addLayout(images, 1)

    def load_preview_items(self):
        image_dir = self.path_from_edit(self.image_edit)
        self.preview_items = (
            sorted(
                (
                    path
                    for path in image_dir.iterdir()
                    if path.is_file() and path.suffix.lower() in _IMAGE_SUFFIXES
                ),
                key=natural_sort_key,
            )
            if image_dir.exists()
            else []
        )
        self.preview_index = 0
        self.render_current()

    def prev_image(self):
        if not self.preview_items:
            self.load_preview_items()
            return
        self.preview_index = (self.preview_index - 1) % len(self.preview_items)
        self.render_current()

    def next_image(self):
        if not self.preview_items:
            self.load_preview_items()
            return
        self.preview_index = (self.preview_index + 1) % len(self.preview_items)
        self.render_current()

    def show_preview_index(self, index: int):
        if not self.preview_items:
            self.load_preview_items()
            return
        self.preview_index = index % len(self.preview_items)
        self.render_current()

    def show_preview_list(self):
        if not self.preview_items:
            self.load_preview_items()
        if not self.preview_items:
            QMessageBox.information(
                self, "图片列表", "当前图片文件夹没有可预览的图片。"
            )
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("图片列表")
        dialog.resize(320, 520)
        dialog.setMinimumSize(200, 200)
        layout = QVBoxLayout(dialog)
        listing = QListWidget()
        layout.addWidget(listing, 1)
        search = QLineEdit()
        search.setPlaceholderText("搜索文件名")
        layout.addWidget(search)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        layout.addWidget(buttons)
        visible_paths: list[Path] = []

        def filter_items(text: str = ""):
            nonlocal visible_paths
            needle = text.strip().lower()
            visible_paths = [
                path
                for path in self.preview_items
                if not needle or needle in path.name.lower()
            ]
            listing.clear()
            for path in visible_paths:
                listing.addItem(path.name)
            if visible_paths:
                current_path = (
                    self.preview_items[self.preview_index]
                    if 0 <= self.preview_index < len(self.preview_items)
                    else visible_paths[0]
                )
                current_row = (
                    visible_paths.index(current_path)
                    if current_path in visible_paths
                    else 0
                )
                listing.setCurrentRow(current_row)

        def jump_to_current():
            row = listing.currentRow()
            if 0 <= row < len(visible_paths):
                self.preview_index = self.preview_items.index(visible_paths[row])
                self.render_current()
                dialog.accept()

        filter_items()
        search.textChanged.connect(filter_items)
        listing.itemDoubleClicked.connect(lambda _item: jump_to_current())
        buttons.accepted.connect(jump_to_current)
        buttons.rejected.connect(dialog.reject)
        dialog.exec()

    def render_current(self):
        if not self.preview_items:
            self.current_label.setText("未找到图片")
            return
        image_path = self.preview_items[self.preview_index]
        label_path = self.path_from_edit(self.label_edit) / f"{image_path.stem}.txt"
        self.current_label.setText(
            f"{self.preview_index + 1}/{len(self.preview_items)}  {image_path.name}"
        )
        image = Image.open(image_path).convert("RGB")
        annotations = load_yolo_annotations(
            image.size,
            label_path,
            self.app.settings["task"]["mode"],
            self.app.settings["dataset"]["class_names"],
        )
        preview = render_annotation_preview(image_path, annotations)
        self.source_view.set_pil_image(image)
        self.result_view.set_pil_image(preview)
