from __future__ import annotations

from typing import Callable

from src.shared.qt import (
    QAbstractItemView,
    QComboBox,
    QCheckBox,
    QHeaderView,
    QLineEdit,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    Qt,
)


class MappingComboBox(QComboBox):
    """Keep wheel scrolling on the mapping table instead of changing the value."""

    def wheelEvent(self, event):  # noqa: N802 - Qt API name
        event.ignore()


def configure_mapping_table(table: QTableWidget) -> None:
    table.setHorizontalHeaderLabels(["#", "模型类别", "标注类别", "状态"])
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(38)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    table.setMinimumHeight(140)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    table.horizontalHeader().setSectionResizeMode(
        0, QHeaderView.ResizeMode.ResizeToContents
    )
    table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
    table.horizontalHeader().setSectionResizeMode(
        3, QHeaderView.ResizeMode.ResizeToContents
    )


def _summary_text(total: int, matched: int, skipped: int) -> str:
    return f"共 {total} 个类别 | 已匹配: {matched} | 已跳过: {skipped} | 未处理: 0"


def populate_mapping_table(
    *,
    table: QTableWidget,
    summary: QLabel,
    model_labels: list[str],
    class_names: list[str],
    status_changed: Callable,
) -> list[QComboBox]:
    combos: list[QComboBox] = []
    table.setRowCount(len(model_labels))
    matched = 0
    for row, model_label in enumerate(model_labels):
        index_item = QTableWidgetItem(str(row))
        label_item = QTableWidgetItem(model_label)
        combo = MappingComboBox()
        combo.setMinimumHeight(28)
        combo.setStyleSheet("QComboBox { padding: 2px 6px; }")
        combo.addItem("-- 跳过 --", "")
        for name in class_names:
            combo.addItem(name, name)
        if model_label in class_names:
            combo.setCurrentText(model_label)
            matched += 1
        combo.currentTextChanged.connect(status_changed)
        table.setItem(row, 0, index_item)
        table.setItem(row, 1, label_item)
        table.setCellWidget(row, 2, combo)
        table.setItem(row, 3, QTableWidgetItem(""))
        combos.append(combo)
    update_mapping_status(
        table=table,
        summary=summary,
        model_labels=model_labels,
        mapping_combos=combos,
    )
    summary.setText(_summary_text(len(model_labels), matched, len(model_labels) - matched))
    return combos


def update_mapping_status(
    *,
    table: QTableWidget,
    summary: QLabel,
    model_labels: list[str],
    mapping_combos: list[QComboBox],
) -> None:
    matched = 0
    skipped = 0
    for row, combo in enumerate(mapping_combos):
        value = str(combo.currentData() or "")
        status = "未匹配"
        if value:
            matched += 1
            status = "已匹配"
        else:
            skipped += 1
            status = "跳过"
        item = table.item(row, 3)
        if item is not None:
            item.setText(status)
    if model_labels:
        summary.setText(_summary_text(len(model_labels), matched, skipped))


def collect_mapping(table: QTableWidget, mapping_combos: list[QComboBox]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for row, combo in enumerate(mapping_combos):
        model_label = table.item(row, 1)
        if model_label is None:
            continue
        target = str(combo.currentData() or "")
        if target:
            mapping[model_label.text()] = target
    return mapping


def configure_sam3_prompt_table(table: QTableWidget) -> None:
    table.setColumnCount(4)
    table.setHorizontalHeaderLabels(["启用", "标注类别", "文本提示词", "状态"])
    table.setStyleSheet("QTableWidget::item { padding: 5px; }")
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(38)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    table.setMinimumHeight(140)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
    table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)


def populate_sam3_prompt_table(
    *,
    table: QTableWidget,
    summary: QLabel,
    class_names: list[str],
    saved_prompts: dict[str, str],
    saved_enabled_classes: list[str],
) -> tuple[list[QCheckBox], list[QLineEdit]]:
    checks: list[QCheckBox] = []
    edits: list[QLineEdit] = []
    enabled_saved = {str(value).strip() for value in saved_enabled_classes if str(value).strip()}
    # An entirely empty legacy settings object means "all classes". Once
    # prompts have been saved, an empty enabled list represents the user's
    # intentional choice to disable every row until they re-enable one.
    use_all = not enabled_saved and not saved_prompts
    table.setRowCount(len(class_names))
    for row, class_name in enumerate(class_names):
        check = QCheckBox()
        check.setChecked(use_all or class_name in enabled_saved)
        edit = QLineEdit(str(saved_prompts.get(class_name, class_name)))
        edit.setMinimumHeight(28)
        edit.setStyleSheet("QLineEdit { padding: 0; }")
        edit.setPlaceholderText(class_name)
        table.setCellWidget(row, 0, check)
        table.setItem(row, 1, QTableWidgetItem(class_name))
        table.setCellWidget(row, 2, edit)
        table.setItem(row, 3, QTableWidgetItem("已启用" if check.isChecked() else "跳过"))
        check.stateChanged.connect(
            lambda state, item=table.item(row, 3): item.setText("已启用" if state else "跳过")
        )
        checks.append(check)
        edits.append(edit)
    update_sam3_prompt_status(table, summary, checks, edits)
    return checks, edits


def update_sam3_prompt_status(
    table: QTableWidget,
    summary: QLabel,
    checks: list[QCheckBox],
    edits: list[QLineEdit],
) -> None:
    enabled = 0
    valid = 0
    for check, edit in zip(checks, edits):
        if check.isChecked():
            enabled += 1
            if edit.text().strip():
                valid += 1
    summary.setText(f"已启用 {enabled} 个类别 | 有效提示词 {valid} 个")


