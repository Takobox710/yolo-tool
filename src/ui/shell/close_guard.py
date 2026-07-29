from __future__ import annotations

from src.shared.qt import QMessageBox


NON_BLOCKING_TASK_KINDS = frozenset(
    {"env", "env_auto", "home_summary", "train_status", "release_check"}
)


def confirm_close_if_needed(window) -> bool:
    warnings = collect_close_warnings(window)
    if not warnings:
        return True
    details = "\n".join(f"- {item}" for item in warnings)
    message_box = QMessageBox(
        QMessageBox.Icon.Question,
        "确认关闭程序",
        f"当前还有以下内容未处理：\n{details}\n\n确认继续关闭程序吗？",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        window,
    )
    message_box.button(QMessageBox.StandardButton.Yes).setText("是")
    message_box.button(QMessageBox.StandardButton.No).setText("否")
    result = message_box.exec()
    return result == QMessageBox.StandardButton.Yes


def collect_close_warnings(window) -> list[str]:
    warnings: list[str] = []
    annotation_page = window.pages.get("annotation")
    annotation_target = getattr(annotation_page, "inner_page", annotation_page)
    has_unsaved_annotations = getattr(annotation_target, "has_unsaved_annotations", None)
    if callable(has_unsaved_annotations) and has_unsaved_annotations():
        warnings.append("当前有未保存的标注")
    active_tasks = tuple(
        task
        for task in window.context.tasks.active()
        if task.kind not in NON_BLOCKING_TASK_KINDS
    )
    if active_tasks:
        warnings.append("后台任务尚未结束：" + "、".join(sorted(item.kind for item in active_tasks)))
    return warnings


def is_training_active(window) -> bool:
    return window.context.tasks.is_active("train")
