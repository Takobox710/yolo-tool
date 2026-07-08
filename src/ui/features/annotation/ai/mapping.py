from __future__ import annotations

from typing import Callable

from src.shared.qt import (
    QAbstractItemView,
    QComboBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    Qt,
)


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
        combo = QComboBox()
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


