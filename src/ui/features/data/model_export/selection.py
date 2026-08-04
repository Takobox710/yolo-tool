from __future__ import annotations

from pathlib import Path

from src.services.model_export import (
    download_generic_calibration_pack,
    export_model_display_path,
    find_export_model_paths,
    generic_calibration_pack_path,
)
from src.shared.qt import QFileDialog
from src.ui.shared.workers import Worker


def choose_model(page, combo) -> None:
    start = page.project_root() / "data" / "models"
    start.mkdir(parents=True, exist_ok=True)
    path, _ = QFileDialog.getOpenFileName(
        page, "选择模型文件", str(start), "PyTorch 模型 (*.pt);;所有文件 (*)"
    )
    if path:
        resolved = Path(path).resolve()
        display = model_display_path(page, resolved)
        page._model_display_paths[display] = resolved
        combo.setCurrentText(display)


def refresh_model_choices(page) -> None:
    current = page.model_combo.currentText()
    show_last = page.context.settings.features.show_last_training_models
    paths = find_export_model_paths(
        page.project_root(),
        show_last_training_models=show_last,
    )
    page._model_display_paths = {
        export_model_display_path(path, page.project_root()): path for path in paths
    }
    choices = list(page._model_display_paths)
    page.model_combo.blockSignals(True)
    page.model_combo.clear()
    page.model_combo.addItems(choices)
    if current:
        page.model_combo.setCurrentText(current)
    elif choices:
        page.model_combo.setCurrentIndex(0)
    page.model_combo.blockSignals(False)
    page.update_option_visibility()


def model_display_path(page, value: str | Path) -> str:
    if not value:
        return ""
    path = Path(page.resolve_project_value(str(value)))
    if path.is_file() and path.parent.name.lower() == "weights":
        display = export_model_display_path(path, page.project_root())
        page._model_display_paths[display] = path
        return display
    return page.display_path(value)


def choose_calibration_data(page, edit) -> None:
    current = page.resolve_path_text(edit) if edit.text() else str(page.project_root())
    path, _ = QFileDialog.getOpenFileName(
        page,
        "选择校准数据",
        current,
        "数据集或图片列表 (*.yaml *.yml *.txt);;所有文件 (*)",
    )
    if path:
        edit.setText(page.display_path(path))
        return
    path = QFileDialog.getExistingDirectory(page, "选择校准图片目录", current)
    if path:
        edit.setText(page.display_path(path))


def download_generic_calibration_pack_for(page) -> None:
    if page._calibration_worker is not None:
        return
    existing = generic_calibration_pack_path()
    if existing is not None:
        page.calibration_data_edit.setText(page.display_path(existing))
        page.log.append(f"通用校准集已就绪：{existing}")
        return
    page.calibration_pack_btn.setEnabled(False)
    page.calibration_pack_progress.setValue(0)
    page.calibration_pack_progress.setVisible(True)
    worker = Worker(
        "generic_calibration_pack",
        lambda report: download_generic_calibration_pack(
            progress=lambda downloaded, total: report(
                "下载通用校准集",
                int(downloaded * 100 / total) if total else 0,
            )
        ),
        accepts_progress=True,
    )
    page._calibration_worker = worker
    workers = getattr(page.context, "workers", None)
    if isinstance(workers, list):
        workers.append(worker)
    worker.progress.connect(page._calibration_pack_progress)
    worker.finished_with_payload.connect(page._apply_calibration_pack_result)
    worker.finished.connect(lambda: page._clear_calibration_worker(worker))
    worker.start()


def calibration_pack_progress(page, message: str, value: int) -> None:
    page.calibration_pack_progress.setFormat(f"{message} %p%")
    page.calibration_pack_progress.setValue(value)


def apply_calibration_pack_result(page, _kind: str, payload) -> None:
    if isinstance(payload, dict) and payload.get("error"):
        page.log.append(f"获取通用校准集失败：{payload['error']}")
        return
    path = Path(str(payload))
    page.calibration_data_edit.setText(page.display_path(path))
    page.calibration_pack_progress.setValue(100)
    page.log.append(f"通用校准集已就绪：{path}")


def clear_calibration_worker(page, worker: Worker) -> None:
    workers = getattr(page.context, "workers", None)
    if isinstance(workers, list) and worker in workers:
        workers.remove(worker)
    if page._calibration_worker is worker:
        page._calibration_worker = None
    page.calibration_pack_btn.setEnabled(not page.is_exporting)
    page.calibration_pack_progress.setVisible(False)
