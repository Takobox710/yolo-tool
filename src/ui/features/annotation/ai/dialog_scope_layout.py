from __future__ import annotations

from src.shared.qt import QButtonGroup, QHBoxLayout, QLabel, QRadioButton, QComboBox, QPushButton, QVBoxLayout, QFrame, QWidget


def build_scope_card(dialog):
    options_card = QFrame()
    options_card.setObjectName("card")
    options_layout = QVBoxLayout(options_card)
    options_layout.setContentsMargins(12, 10, 12, 10)
    options_layout.setSpacing(8)
    options_title = QLabel("范围与模式")
    options_title.setObjectName("sectionTitle")
    options_layout.addWidget(options_title)
    
    range_row = QHBoxLayout()
    range_row.setContentsMargins(0, 0, 0, 0)
    range_row.setSpacing(8)
    range_label = QLabel("标注范围:")
    range_label.setObjectName("annotationPathLabel")
    range_row.addWidget(range_label)
    dialog.range_combo = QComboBox()
    dialog.range_combo.addItems(
        ["当前图片", "当前及以后图片", "全部未标注图片", "全部图片", "自定义图片"]
    )
    dialog.range_combo.currentTextChanged.connect(dialog.on_range_mode_changed)
    dialog.range_combo.setCurrentText(dialog.saved_range_mode)
    range_row.addWidget(dialog.range_combo, 1)
    dialog.range_count_label = QLabel("")
    dialog.range_count_label.setObjectName("fieldLabel")
    range_row.addWidget(dialog.range_count_label)
    dialog.range_list_btn = QPushButton("图片列表")
    dialog.range_list_btn.setObjectName("softButton")
    dialog.range_list_btn.clicked.connect(dialog.open_custom_image_list)
    dialog.range_list_btn.hide()
    range_row.addWidget(dialog.range_list_btn)
    options_layout.addLayout(range_row)
    
    process_row = QHBoxLayout()
    process_row.setContentsMargins(0, 0, 0, 0)
    process_row.setSpacing(8)
    process_label = QLabel("处理模式:")
    process_label.setObjectName("annotationPathLabel")
    process_row.addWidget(process_label)
    dialog.append_radio = QRadioButton("追加")
    dialog.append_radio.setToolTip("保留原有标注，并追加 AI 识别出的新标注。")
    dialog.replace_radio = QRadioButton("替换")
    dialog.replace_radio.setToolTip("清除原有标注，仅保留本次 AI 预标注结果。")
    dialog.append_radio.setChecked(dialog.saved_process_mode != "替换")
    dialog.replace_radio.setChecked(dialog.saved_process_mode == "替换")
    dialog.process_group = QButtonGroup(dialog)
    dialog.process_group.addButton(dialog.append_radio)
    dialog.process_group.addButton(dialog.replace_radio)
    process_row.addWidget(dialog.append_radio)
    process_row.addWidget(dialog.replace_radio)
    process_row.addStretch(1)
    options_layout.addLayout(process_row)
    options_layout.addStretch(1)
    return options_card


__all__ = ["build_scope_card"]
