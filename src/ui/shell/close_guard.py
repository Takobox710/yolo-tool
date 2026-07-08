from __future__ import annotations

from src.shared.qt import QMessageBox


def confirm_close_if_needed(window) -> bool:
    warnings = collect_close_warnings(window)
    if not warnings:
        return True
    details = "\n".join(f"- {item}" for item in warnings)
    result = QMessageBox.question(
        window,
        "确认关闭程序",
        f"当前还有以下内容未处理：\n{details}\n\n确认继续关闭程序吗？",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return result == QMessageBox.StandardButton.Yes


def collect_close_warnings(window) -> list[str]:
    warnings: list[str] = []
    annotation_page = window.pages.get("annotation")
    annotation_target = getattr(annotation_page, "inner_page", annotation_page)
    has_unsaved_annotations = getattr(annotation_target, "has_unsaved_annotations", None)
    if callable(has_unsaved_annotations) and has_unsaved_annotations():
        warnings.append("当前有未保存的标注")
    if is_training_active(window):
        warnings.append("模型训练尚未结束")
    return warnings


def is_training_active(window) -> bool:
    train_page = window.pages.get("train")
    train_target = getattr(train_page, "inner_page", train_page)
    if bool(getattr(train_target, "is_training", False)):
        return True
    handle = getattr(window, "training_handle", None)
    if handle is None:
        return False
    process = getattr(handle, "process", None)
    poll = getattr(process, "poll", None)
    if callable(poll):
        return poll() is None
    return True

