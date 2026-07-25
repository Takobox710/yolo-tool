from __future__ import annotations

from pathlib import Path

from src.services.model_export import (
    inspect_extension_package_fast,
    install_extension_package,
    is_extension_package_path,
    load_installed_extension,
)
from src.services.runtime import invalidate_cache
from src.shared.qt import QEvent, QFileDialog, QMessageBox, QWidget
from src.ui.shared.workers import Worker


class ModelExportPackageDropMixin:
    def setup_model_export_package_drop(self) -> None:
        self.setAcceptDrops(True)
        self.model_export_install_worker: Worker | None = None

    def finalize_model_export_package_drop(self) -> None:
        for child in self.findChildren(QWidget):
            child.installEventFilter(self)

    def choose_model_export_package(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择模型转换附加包",
            str(self.project_root()),
            "模型转换附加包 (*.7z *.zip);;7z 压缩包 (*.7z);;ZIP 压缩包 (*.zip)",
        )
        if path:
            self.confirm_model_export_package(Path(path))

    def dragEnterEvent(self, event):  # noqa: N802 - Qt API name
        if self._extension_path_from_event(event) is not None:
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event):  # noqa: N802 - Qt API name
        path = self._extension_path_from_event(event)
        if path is None:
            event.ignore()
            return
        event.acceptProposedAction()
        self.confirm_model_export_package(path)

    def eventFilter(self, watched, event):  # noqa: N802 - Qt API name
        if event.type() in {
            QEvent.Type.DragEnter,
            QEvent.Type.DragMove,
            QEvent.Type.Drop,
        }:
            path = self._extension_path_from_event(event)
            if path is not None:
                if event.type() == QEvent.Type.Drop:
                    self.confirm_model_export_package(path)
                event.acceptProposedAction()
                return True
        return super().eventFilter(watched, event)

    def confirm_model_export_package(self, path: Path) -> None:
        if self.model_export_install_worker is not None:
            QMessageBox.information(self, "正在安装", "模型转换附加包正在安装，请稍候。")
            return
        try:
            manifest = inspect_extension_package_fast(path)
        except Exception as exc:
            QMessageBox.warning(self, "无法识别附加包", str(exc))
            return
        formats = ", ".join(str(item) for item in manifest.get("supported_formats", ()))
        installed = load_installed_extension()
        action = (
            f"当前已安装附加环境 {installed.version}，继续操作将替换已有安装。\n\n"
            if installed is not None
            else ""
        )
        answer = QMessageBox.question(
            self,
            "添加模型转换附加包",
            f"{action}识别到模型转换附加包 {manifest['version']}。\n"
            f"支持格式：{formats}\n\n是否添加并启用？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.install_model_export_package(path)

    def install_model_export_package(self, path: Path) -> None:
        self._notify_model_export_installing(True)
        worker = Worker(
            "model_export_install",
            lambda report: install_extension_package(path, progress=report),
            accepts_progress=True,
        )
        self.model_export_install_worker = worker
        workers = getattr(self.context, "workers", None)
        if isinstance(workers, list):
            workers.append(worker)
        worker.finished_with_payload.connect(self._apply_model_export_install_result)
        worker.progress.connect(self._model_export_install_progress)
        worker.finished.connect(lambda: self._clear_model_export_install_worker(worker))
        worker.start()

    def _model_export_install_progress(self, message: str, value: int) -> None:
        hook = getattr(self, "model_export_package_install_progress", None)
        if hook:
            hook(message, value)

    def _apply_model_export_install_result(self, _kind: str, payload) -> None:
        if isinstance(payload, dict) and payload.get("error"):
            QMessageBox.warning(self, "附加包安装失败", payload["error"])
            return
        invalidate_cache("dependency_versions")
        QMessageBox.information(
            self,
            "附加包安装完成",
            f"已启用模型转换附加环境 {payload.version}。",
        )
        hook = getattr(self, "model_export_package_installed", None)
        if hook:
            hook(payload)

    def _clear_model_export_install_worker(self, worker: Worker) -> None:
        workers = getattr(self.context, "workers", None)
        if isinstance(workers, list) and worker in workers:
            workers.remove(worker)
        if self.model_export_install_worker is worker:
            self.model_export_install_worker = None
        self._notify_model_export_installing(False)

    def _notify_model_export_installing(self, installing: bool) -> None:
        hook = getattr(self, "model_export_package_installing_changed", None)
        if hook:
            hook(installing)

    @staticmethod
    def _extension_path_from_event(event) -> Path | None:
        mime = event.mimeData()
        if not mime.hasUrls():
            return None
        for url in mime.urls():
            if not url.isLocalFile():
                continue
            path = Path(url.toLocalFile())
            if is_extension_package_path(path):
                return path
        return None
