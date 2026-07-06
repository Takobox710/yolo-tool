from __future__ import annotations

from scr.ui.qt import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    Qt,
    QVBoxLayout,
    QWidget,
)


class FormPageMixin:
    def _set_help_target(self, widget, base_text: str, help_text: str):
        widget.setProperty("helpBaseText", base_text)
        widget.setProperty("helpText", help_text)
        self._refresh_help_target(widget)

    def _refresh_help_target(self, widget):
        base_text = widget.property("helpBaseText")
        help_text = widget.property("helpText")
        if base_text is None:
            return
        base_text = str(base_text)
        help_text = str(help_text or "")
        show_symbol = self.help_icons_enabled() and bool(help_text)
        widget.setText(f"{base_text} ⓘ" if show_symbol else base_text)
        widget.setToolTip(help_text)

    def _caption_widget(
        self,
        label: str,
        help_text: str = "",
        object_name: str = "fieldLabel",
        fixed_width: int | None = None,
    ):
        box = QWidget()
        layout = QHBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        caption = QLabel(label)
        caption.setObjectName(object_name)
        self._set_help_target(caption, label, help_text)
        layout.addWidget(caption)
        layout.addStretch(1)
        if fixed_width is not None:
            box.setFixedWidth(fixed_width)
        return box, caption, None

    def checkbox_with_help(
        self, text: str, checked: bool = False, help_text: str = ""
    ):
        box = QWidget()
        layout = QHBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        check = QCheckBox(text)
        check.setChecked(checked)
        self._set_help_target(check, text, help_text)
        layout.addWidget(check)
        layout.addStretch(1)
        return box, check

    def field(
        self,
        label: str,
        value: str = "",
        browse=None,
        placeholder: str = "",
        help_text: str = "",
    ):
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        caption_box, _caption, _icon = self._caption_widget(
            label, help_text=help_text, object_name="fieldLabel"
        )
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        edit = QLineEdit(str(value))
        if placeholder:
            edit.setPlaceholderText(placeholder)
        row.addWidget(edit, 1)
        if browse:
            button = QPushButton("选择")
            button.setObjectName("softButton")
            button.clicked.connect(lambda: browse(edit))
            row.addWidget(button)
        layout.addWidget(caption_box)
        layout.addLayout(row)
        return box, edit

    def path_field(
        self,
        label: str,
        value: str = "",
        browse=None,
        placeholder: str = "",
        help_text: str = "",
    ):
        return self.field(
            label,
            self.display_path(value),
            browse,
            placeholder,
            help_text=help_text,
        )

    def combo_field(
        self,
        label: str,
        value: str,
        values: list[str],
        help_text: str = "",
        *,
        editable: bool = False,
        placeholder: str = "",
    ):
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        caption_box, _caption, _icon = self._caption_widget(
            label, help_text=help_text, object_name="fieldLabel"
        )
        combo = QComboBox()
        combo.setEditable(editable)
        combo.addItems(values)
        if editable:
            self._configure_editable_combo(combo, placeholder)
        if str(value):
            combo.setCurrentText(str(value))
        layout.addWidget(caption_box)
        layout.addWidget(combo)
        return box, combo

    def inline_field(
        self,
        label: str,
        value: str = "",
        browse=None,
        placeholder: str = "",
        help_text: str = "",
        *,
        label_width: int = 88,
    ):
        box = QWidget()
        layout = QHBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        caption_box, _caption, _icon = self._caption_widget(
            label,
            help_text=help_text,
            object_name="inlineFieldLabel",
            fixed_width=label_width,
        )
        edit = QLineEdit(str(value))
        if placeholder:
            edit.setPlaceholderText(placeholder)
        layout.addWidget(caption_box)
        layout.addWidget(edit, 1)
        if browse:
            button = QPushButton("选择")
            button.setObjectName("softButton")
            button.clicked.connect(lambda: browse(edit))
            layout.addWidget(button)
        return box, edit

    def inline_combo_field(
        self,
        label: str,
        value: str,
        values: list[str],
        help_text: str = "",
        *,
        editable: bool = False,
        placeholder: str = "",
        label_width: int = 88,
    ):
        box = QWidget()
        layout = QHBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        caption_box, _caption, _icon = self._caption_widget(
            label,
            help_text=help_text,
            object_name="inlineFieldLabel",
            fixed_width=label_width,
        )
        combo = QComboBox()
        combo.setEditable(editable)
        combo.addItems(values)
        if editable:
            self._configure_editable_combo(combo, placeholder)
        if str(value):
            combo.setCurrentText(str(value))
        layout.addWidget(caption_box)
        layout.addWidget(combo, 1)
        return box, combo

    def stacked_field(
        self,
        label: str,
        value: str = "",
        browse=None,
        placeholder: str = "",
        help_text: str = "",
    ):
        box = QWidget()
        outer = QVBoxLayout(box)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)
        caption_box, _caption, _icon = self._caption_widget(
            label, help_text=help_text, object_name="fieldLabel"
        )
        outer.addWidget(caption_box)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        edit = QLineEdit(str(value))
        if placeholder:
            edit.setPlaceholderText(placeholder)
        row.addWidget(edit, 1)
        if browse:
            btn = QPushButton("选择")
            btn.setObjectName("softButton")
            btn.clicked.connect(lambda: browse(edit))
            row.addWidget(btn)
        outer.addLayout(row)
        return box, edit

    def stacked_path_field(
        self,
        label: str,
        value: str = "",
        browse=None,
        placeholder: str = "",
        help_text: str = "",
    ):
        return self.stacked_field(
            label,
            self.display_path(value),
            browse,
            placeholder,
            help_text=help_text,
        )

    def stacked_combo_field(
        self,
        label: str,
        value: str,
        values: list[str],
        browse=None,
        placeholder: str = "",
        help_text: str = "",
    ):
        box = QWidget()
        outer = QVBoxLayout(box)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)
        caption_box, _caption, _icon = self._caption_widget(
            label, help_text=help_text, object_name="fieldLabel"
        )
        outer.addWidget(caption_box)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        combo = QComboBox()
        combo.setEditable(True)
        combo.addItems(values)
        self._configure_editable_combo(combo, placeholder)
        if str(value):
            combo.setCurrentText(str(value))
        row.addWidget(combo, 1)
        if browse:
            btn = QPushButton("选择")
            btn.setObjectName("softButton")
            btn.clicked.connect(lambda: browse(combo))
            row.addWidget(btn)
        outer.addLayout(row)
        return box, combo

    def _configure_editable_combo(
        self, combo: QComboBox, placeholder: str = ""
    ) -> None:
        line_edit = combo.lineEdit()
        if line_edit is None:
            return
        line_edit.setFrame(False)
        line_edit.setContentsMargins(0, 0, 0, 0)
        line_edit.setTextMargins(0, 0, 0, 0)
        line_edit.setStyleSheet(
            "QLineEdit { background: transparent; border: 0; padding: 0; margin: 0; }"
        )
        if placeholder:
            line_edit.setPlaceholderText(placeholder)

    def choose_dir(self, edit: QLineEdit):
        current = self.resolve_path_text(edit) if edit.text() else str(self.project_root())
        path = QFileDialog.getExistingDirectory(self, "选择文件夹", current)
        if path:
            edit.setText(self.display_path(path))

    def choose_file(self, edit: QLineEdit, caption: str = "选择文件"):
        current = self.resolve_path_text(edit) if edit.text() else str(self.project_root())
        path, _ = QFileDialog.getOpenFileName(self, caption, current, "All Files (*)")
        if path:
            edit.setText(self.display_path(path))

    def _choose_pt_for_combo(self, combo: QComboBox):
        models_dir = self.project_root() / "data" / "models"
        models_dir.mkdir(parents=True, exist_ok=True)
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择模型文件",
            str(models_dir),
            "PyTorch 模型 (*.pt);;所有文件 (*)",
        )
        if path:
            combo.setCurrentText(self.display_path(path))

    def stat_card(self, label: str, value: str = "-"):
        card = QFrame()
        card.setObjectName("statCard")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)
        name = QLabel(label)
        name.setObjectName("fieldLabel")
        name.setFixedWidth(90)
        metric = QLabel(value)
        metric.setObjectName("statValue")
        metric.setWordWrap(False)
        metric.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        metric.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        layout.addWidget(name)
        layout.addWidget(metric, 1)
        return card, metric

    def metric_card(self, label: str, value: str = "待检测"):
        card = QFrame()
        card.setObjectName("metricCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        name = QLabel(label)
        name.setObjectName("fieldLabel")
        metric = QLabel(value)
        metric.setObjectName("metricValue")
        metric.setWordWrap(True)
        layout.addWidget(name)
        layout.addWidget(metric)
        return card, metric
