from __future__ import annotations

import json
from pathlib import Path

from PIL import Image
from PySide6.QtGui import QKeySequence

from scr.services.editable_annotation_service import (
    EditableAnnotation,
    load_editable_annotations,
    load_labelme_annotations,
    save_editable_annotations,
    save_labelme_annotations,
)
from scr.services.rename_service import natural_sort_key
from scr.ui.page_base import BasePage, _IMAGE_SUFFIXES
from scr.ui.qt import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QShortcut,
    QStyle,
    Qt,
    QVBoxLayout,
)
from scr.ui.views.annotation_ai_dialog import AiPrelabelDialog, CustomAiImageSelectionDialog
from scr.ui.views.annotation_canvas import AnnotationCanvas
from scr.ui.views.annotation_dialogs import (
    AnnotationSettingsDialog,
    ClassManagerDialog,
    DrawShapeDialog,
)


_SHAPE_LABELS = {
    "rect": "矩形框",
    "circle": "圆形",
    "obb": "有向矩形",
    "obb_mirror": "镜像有向矩形",
    "obb_single": "有向矩形",
    "polygon": "多边形",
    "line_expand": "直线拓展",
}


class AnnotationPage(BasePage):
    def __init__(self, app):
        super().__init__(app)
        self.image_items: list[Path] = []
        self.current_index = -1
        self.dirty = False
        self.current_json_path: Path | None = None
        self.current_yolo_path: Path | None = None
        self.current_image_path: Path | None = None
        self.output_mode = self.app.settings.get("task", {}).get("mode", "detect")
        self.current_class_id = 0

        root = QHBoxLayout(self)
        root.setContentsMargins(20, 14, 12, 12)
        root.setSpacing(8)
        root.addWidget(self._build_toolbar())
        root.addLayout(self._build_center(), 1)
        root.addWidget(self._build_right_panel())

        self._refresh_class_state()
        self._refresh_path_labels()
        delete_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Delete), self)
        delete_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        delete_shortcut.activated.connect(self.delete_selected)
        self._delete_shortcut = delete_shortcut
        self.scan_images(select_first=True)

    def _build_toolbar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("annotationSidebar")
        sidebar.setFixedWidth(178)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 22, 16, 18)
        layout.setSpacing(13)
        title = QLabel("数据标注")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("annotationTitle")
        self._set_help_target(
            title,
            "数据标注",
            "可通过右键菜单快速切换标注类型，默认保存和读取 Labelme 格式标注；可通过“更多设置”开启 YOLO 格式文件保存。",
        )
        layout.addWidget(title)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("annotationDivider")
        layout.addWidget(line)
        image_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)
        for text, slot, icon in [
            ("图片文件夹", self.choose_image_dir, image_icon),
            ("标签文件夹", self.choose_label_dir, image_icon),
            ("⬅️上一张(A)", self.prev_image, None),
            ("➡️下一张(D)", self.next_image, None),
            ("✎ 画标注框(W)", self.enable_draw_mode, None),
        ]:
            button = QPushButton(text)
            button.setObjectName("annotationToolButton")
            if text in {"⬅️上一张(A)", "➡️下一张(D)"}:
                button.setProperty("compactArrowButton", True)
                button.style().unpolish(button)
                button.style().polish(button)
            if icon is not None:
                button.setIcon(icon)
            button.clicked.connect(slot)
            layout.addWidget(button)
        ai_btn = QPushButton("🤖 AI预标注")
        ai_btn.setObjectName("annotationToolButton")
        ai_btn.clicked.connect(self.open_ai_prelabel_dialog)
        layout.addWidget(ai_btn)
        settings_btn = QPushButton("⚙ 更多设置")
        settings_btn.setObjectName("annotationToolButton")
        settings_btn.clicked.connect(self.open_annotation_settings)
        layout.addWidget(settings_btn)
        layout.addStretch(1)
        return sidebar

    def _build_center(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 2, 0, 0)
        layout.setSpacing(0)
        self.canvas = AnnotationCanvas()
        self.canvas.changed_callback = self.mark_dirty_and_save
        self.canvas.selection_callback = self.sync_selection
        layout.addWidget(self.canvas, 1)
        return layout

    def _build_right_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("annotationRightPanel")
        panel.setFixedWidth(230)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        mode_label = QLabel("任务类别：")
        mode_label.setObjectName("annotationPathLabel")
        layout.addWidget(mode_label)
        self.output_mode_combo = QComboBox()
        self.output_mode_combo.addItems(["detect", "obb"])
        self.output_mode_combo.setCurrentText(
            self.output_mode if self.output_mode in {"detect", "obb"} else "detect"
        )
        self.output_mode_combo.currentTextChanged.connect(self.change_output_mode)
        layout.addWidget(self.output_mode_combo)
        class_label = QLabel("标注类别：")
        class_label.setObjectName("annotationPathLabel")
        layout.addWidget(class_label)
        self.class_combo = QComboBox()
        self.class_combo.currentIndexChanged.connect(self.change_class)
        layout.addWidget(self.class_combo)
        manage_btn = QPushButton("🏷 管理类别")
        manage_btn.setObjectName("annotationPrimaryButton")
        manage_btn.clicked.connect(self.manage_classes)
        layout.addWidget(manage_btn)
        self.annotation_list = QListWidget()
        self.annotation_list.currentRowChanged.connect(self.select_annotation)
        layout.addWidget(self.annotation_list, 2)
        delete_btn = QPushButton("🗑 删除选中框(Del)")
        delete_btn.setObjectName("annotationPrimaryButton")
        delete_btn.clicked.connect(self.delete_selected)
        layout.addWidget(delete_btn)
        file_header = QHBoxLayout()
        file_header.setContentsMargins(0, 0, 0, 0)
        file_header.setSpacing(6)
        file_label = QLabel("图片列表：")
        file_label.setObjectName("annotationPathLabel")
        file_header.addWidget(file_label)
        file_header.addStretch(1)
        self.file_count_label = QLabel("0/0")
        self.file_count_label.setObjectName("annotationPathLabel")
        file_header.addWidget(self.file_count_label)
        layout.addLayout(file_header)
        self.file_list = QListWidget()
        self.file_list.currentRowChanged.connect(self.jump_to_file)
        layout.addWidget(self.file_list, 3)
        return panel

    def choose_image_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "选择图片文件夹", str(self.path_from_setting("images_dir"))
        )
        if not directory:
            return
        self.save_current()
        self.update_setting("paths", "images_dir", value=directory)
        self._refresh_path_labels()
        self.scan_images(select_first=True)

    def choose_label_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "选择 Labelme JSON 标签文件夹", str(self.path_from_setting("annotations_dir"))
        )
        if not directory:
            return
        self.save_current()
        self.update_setting("paths", "annotations_dir", value=directory)
        Path(directory).mkdir(parents=True, exist_ok=True)
        self._refresh_path_labels()
        self.load_current()
        self.refresh_file_list()

    def path_from_setting(self, key: str) -> Path:
        return Path(self.app.settings["paths"][key])

    def scan_images(self, *, select_first: bool) -> None:
        image_dir = self.path_from_setting("images_dir")
        self.image_items = (
            sorted(
                [
                    path
                    for path in image_dir.iterdir()
                    if path.is_file() and path.suffix.lower() in _IMAGE_SUFFIXES
                ],
                key=natural_sort_key,
            )
            if image_dir.exists()
            else []
        )
        if select_first and self.image_items:
            self.current_index = 0
        elif self.current_index >= len(self.image_items):
            self.current_index = 0 if self.image_items else -1
        self.refresh_file_list()
        if self.current_index >= 0:
            self.file_list.setCurrentRow(self.current_index)
            self.load_current()
        else:
            self._update_file_count_label()
            self.canvas.set_image(None, [], self.class_names())

    def prev_image(self) -> None:
        if not self.image_items:
            self.scan_images(select_first=True)
            return
        self.change_current_index((self.current_index - 1) % len(self.image_items))

    def next_image(self) -> None:
        if not self.image_items:
            self.scan_images(select_first=True)
            return
        self.change_current_index((self.current_index + 1) % len(self.image_items))

    def jump_to_file(self, row: int) -> None:
        if 0 <= row < len(self.image_items) and row != self.current_index:
            self.change_current_index(row)

    def change_current_index(self, index: int) -> None:
        self.save_current()
        self.current_index = index
        self.file_list.blockSignals(True)
        self.file_list.setCurrentRow(index)
        self.file_list.blockSignals(False)
        self._update_file_count_label()
        self.load_current()

    def load_current(self) -> None:
        if not (0 <= self.current_index < len(self.image_items)):
            return
        image_path = self.image_items[self.current_index]
        json_path = self.path_from_setting("annotations_dir") / f"{image_path.stem}.json"
        yolo_path = self.path_from_setting("labels_dir") / f"{image_path.stem}.txt"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        yolo_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with Image.open(image_path) as image:
                image_size = image.size
        except OSError as exc:
            QMessageBox.warning(self, "数据标注", f"无法打开图片：{exc}")
            return
        if json_path.exists():
            annotations, class_names = load_labelme_annotations(
                image_size,
                json_path,
                self.class_names(),
                self.app.settings.get("annotation", {}).get("line_expand_pixels", 10),
            )
            if class_names != self.class_names():
                self.app.settings.setdefault("dataset", {})["class_names"] = class_names
                self.save_settings()
                self._refresh_class_state()
        else:
            annotations = load_editable_annotations(image_size, yolo_path)
        self.current_json_path = json_path
        self.current_yolo_path = yolo_path
        self.current_image_path = image_path
        self.canvas.set_image(image_path, annotations, self.class_names())
        self.dirty = False
        self.refresh_annotation_list()
        self._update_current_file_list_item()

    def save_current(self, *, force: bool = False, save_json: bool = True) -> None:
        if not self.dirty and not force:
            return
        if self.current_json_path is None or self.current_image_path is None:
            return
        if self.canvas.image_size == (0, 0):
            return
        annotation_settings = self.app.settings.get("annotation", {})
        if save_json:
            save_labelme_annotations(
                self.canvas.image_size,
                self.current_json_path,
                self.current_image_path,
                self.canvas.annotations,
                self.class_names(),
            )
        if (
            annotation_settings.get("auto_convert_yolo", False) or force
        ) and self.current_yolo_path is not None:
            save_editable_annotations(
                self.canvas.image_size,
                self.current_yolo_path,
                self.canvas.annotations,
                self.output_mode,
            )
        if save_json:
            self.dirty = False

    def mark_dirty_and_save(self) -> None:
        self.dirty = True
        self.refresh_annotation_list()
        annotation_settings = self.app.settings.get("annotation", {})
        if annotation_settings.get("auto_save", True) or annotation_settings.get(
            "auto_convert_yolo", False
        ):
            self.save_current(save_json=annotation_settings.get("auto_save", True))

    def class_names(self) -> list[str]:
        names = [
            str(name).strip()
            for name in self.app.settings.get("dataset", {}).get("class_names", [])
            if str(name).strip()
        ]
        return names or ["weld"]

    def _refresh_class_state(self) -> None:
        names = self.class_names()
        self.current_class_id = min(max(self.current_class_id, 0), len(names) - 1)
        if hasattr(self, "class_combo"):
            self.class_combo.blockSignals(True)
            self.class_combo.clear()
            self.class_combo.addItems(names)
            self.class_combo.setCurrentIndex(self.current_class_id)
            self.class_combo.blockSignals(False)
        self.canvas.set_current_class(self.current_class_id) if hasattr(self, "canvas") else None
        self.canvas.set_class_names(names) if hasattr(self, "canvas") else None
        if hasattr(self, "canvas"):
            annotation_settings = self.app.settings.get("annotation", {})
            self.canvas.set_line_expand_config(
                annotation_settings.get("line_expand_enabled", False),
                annotation_settings.get("line_expand_pixels", 10),
            )
            self.canvas.set_interaction_config(
                annotation_settings.get("continuous_draw", False),
                annotation_settings.get("quick_draw", True),
            )

    def _refresh_path_labels(self) -> None:
        return None

    def change_class(self, index: int) -> None:
        self.current_class_id = max(0, index)
        self.canvas.set_current_class(self.current_class_id)

    def change_shape(self, text: str) -> None:
        mapping = {
            "矩形框": "rect",
            "圆形": "circle",
            "镜像有向矩形": "obb_mirror",
            "有向矩形": "obb_single",
            "多边形": "polygon",
            "直线扩展": "line_expand",
        }
        self.canvas.set_draw_shape(mapping.get(text, "rect"))

    def change_output_mode(self, text: str) -> None:
        mode = text if text in {"detect", "obb"} else "detect"
        self.output_mode = mode
        self.app.settings.setdefault("task", {})["mode"] = mode
        self.save_settings()
        if self.current_json_path is not None:
            self.dirty = True
            self.save_current()

    def enable_draw_mode(self) -> None:
        dialog = DrawShapeDialog(self.canvas.line_expand_enabled, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.canvas.set_draw_shape(dialog.selected_shape)
        self.canvas.setFocus()

    def open_ai_prelabel_dialog(self) -> None:
        dialog = AiPrelabelDialog(self, self)
        dialog.exec()

    def open_annotation_settings(self) -> None:
        current = self.app.settings.get("annotation", {})
        dialog = AnnotationSettingsDialog(
            current.get("line_expand_enabled", False),
            current.get("line_expand_pixels", 10),
            current.get("auto_save", True),
            current.get("auto_convert_yolo", False),
            current.get("continuous_draw", False),
            current.get("quick_draw", True),
            str(self.path_from_setting("labels_dir")),
            self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        (
            enabled,
            pixels,
            auto_save,
            auto_convert_yolo,
            continuous_draw,
            quick_draw,
            yolo_dir,
        ) = dialog.values()
        self.app.settings.setdefault("annotation", {})["line_expand_enabled"] = enabled
        self.app.settings["annotation"]["line_expand_pixels"] = pixels
        self.app.settings["annotation"]["auto_save"] = auto_save
        self.app.settings["annotation"]["auto_convert_yolo"] = auto_convert_yolo
        self.app.settings["annotation"]["continuous_draw"] = continuous_draw
        self.app.settings["annotation"]["quick_draw"] = quick_draw
        if yolo_dir:
            self.app.settings.setdefault("paths", {})["labels_dir"] = yolo_dir
            Path(yolo_dir).mkdir(parents=True, exist_ok=True)
        self.save_settings()
        self._refresh_class_state()
        if auto_save or auto_convert_yolo:
            self.save_current(force=True)

    def manage_classes(self) -> None:
        dialog = ClassManagerDialog(self.class_names(), self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.app.settings.setdefault("dataset", {})["class_names"] = dialog.class_names
        self.save_settings()
        self._refresh_class_state()
        self.canvas.set_class_names(dialog.class_names)
        self.refresh_annotation_list()

    def select_annotation(self, row: int) -> None:
        if row == self.canvas.selected_index:
            return
        self.canvas.selected_index = row
        self.canvas.update()

    def sync_selection(self, row: int) -> None:
        self.annotation_list.blockSignals(True)
        self.annotation_list.setCurrentRow(row)
        self.annotation_list.blockSignals(False)

    def refresh_annotation_list(self) -> None:
        names = self.class_names()
        self.annotation_list.blockSignals(True)
        self.annotation_list.clear()
        for index, annotation in enumerate(self.canvas.annotations):
            label = (
                names[annotation.class_id]
                if 0 <= annotation.class_id < len(names)
                else str(annotation.class_id)
            )
            shape_text = _SHAPE_LABELS.get(annotation.shape, annotation.shape)
            format_text = "obb" if annotation.shape in {"obb", "obb_mirror", "obb_single", "line_expand"} else "detect"
            item = QListWidgetItem(f"{index + 1}.{label}-{shape_text}（{format_text}）")
            self.annotation_list.addItem(item)
        self.annotation_list.setCurrentRow(self.canvas.selected_index)
        self.annotation_list.blockSignals(False)
        self._update_current_file_list_item()

    def _has_annotation_for_image(self, image_path: Path) -> bool:
        if self.current_image_path == image_path and bool(self.canvas.annotations):
            return True
        json_path = self.path_from_setting("annotations_dir") / f"{image_path.stem}.json"
        yolo_path = self.path_from_setting("labels_dir") / f"{image_path.stem}.txt"
        if json_path.exists():
            try:
                payload = json.loads(json_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return False
            return bool(payload.get("shapes"))
        if yolo_path.exists():
            try:
                return any(
                    line.strip()
                    for line in yolo_path.read_text(encoding="utf-8").splitlines()
                )
            except OSError:
                return False
        return False

    def _update_file_count_label(self) -> None:
        total = len(self.image_items)
        current = self.current_index + 1 if 0 <= self.current_index < total else 0
        if hasattr(self, "file_count_label"):
            self.file_count_label.setText(f"{current}/{total}")

    def _current_image_has_annotations(self) -> bool:
        return bool(self.canvas.annotations)

    def _update_current_file_list_item(self) -> None:
        if not hasattr(self, "file_list"):
            return
        if not (0 <= self.current_index < len(self.image_items)):
            return
        item = self.file_list.item(self.current_index)
        if item is None:
            return
        widget = self.file_list.itemWidget(item)
        if isinstance(widget, QCheckBox):
            widget.setChecked(self._current_image_has_annotations())

    def refresh_file_list(self) -> None:
        if not hasattr(self, "file_list"):
            return
        self.file_list.blockSignals(True)
        self.file_list.clear()
        for path in self.image_items:
            item = QListWidgetItem()
            checkbox = QCheckBox(path.name)
            checkbox.setChecked(self._has_annotation_for_image(path))
            checkbox.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            checkbox.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            item.setSizeHint(checkbox.sizeHint())
            self.file_list.addItem(item)
            self.file_list.setItemWidget(item, checkbox)
        self.file_list.blockSignals(False)
        if 0 <= self.current_index < len(self.image_items):
            self.file_list.blockSignals(True)
            self.file_list.setCurrentRow(self.current_index)
            self.file_list.blockSignals(False)
        self._update_file_count_label()

    def delete_selected(self) -> None:
        self.canvas.delete_selected()

    def keyPressEvent(self, event):  # noqa: N802 - Qt API name
        if event.key() == Qt.Key.Key_Delete:
            self.delete_selected()
            return
        if event.key() == Qt.Key.Key_A:
            self.prev_image()
            return
        if event.key() == Qt.Key.Key_D:
            self.next_image()
            return
        super().keyPressEvent(event)

    def on_show(self) -> None:
        self._refresh_path_labels()
        if not self.image_items:
            self.scan_images(select_first=True)


__all__ = [
    "AnnotationPage",
    "EditableAnnotation",
    "load_editable_annotations",
    "load_labelme_annotations",
    "save_editable_annotations",
    "save_labelme_annotations",
    "AnnotationCanvas",
    "AnnotationSettingsDialog",
    "DrawShapeDialog",
    "CustomAiImageSelectionDialog",
    "AiPrelabelDialog",
    "ClassManagerDialog",
]
