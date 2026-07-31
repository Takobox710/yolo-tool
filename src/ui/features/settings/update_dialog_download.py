from __future__ import annotations

import sys
from pathlib import Path

from src.services.runtime.release_updates import (
    check_latest_release,
    download_release_assets,
    launch_installer,
    pause_installer,
    resume_installer,
)
from src.services.runtime.variant import variant_asset_prefix
from src.ui.features.settings.update_dialog_state import (
    apply_download_detail as _apply_download_detail,
    build_download_progress_reporter as _build_download_progress_reporter,
    download_weights as _download_weights,
    update_download_speed as _update_download_speed,
)
from src.ui.shared.workers import Worker


class ReleaseUpdateDownloadMixin:

    def _toggle_pause(self) -> None:
        if self._worker is not None:
            if self._pause_event.is_set():
                self._pause_event.clear()
                self._speed_baseline_downloaded = self._latest_downloaded
                self._download_speed_timer.start()
                self.pause_button.setText("暂停下载")
                self._set_progress_message("正在继续下载…")
            else:
                self._pause_event.set()
                self._download_speed_timer.stop()
                self._speed_baseline_downloaded = self._latest_downloaded
                self.download_speed_label.setText("下载速度：0 B/s")
                self.pause_button.setText("继续下载")
                self._set_progress_message("下载已暂停。")
            return
        if self._installer_process is None:
            return
        try:
            dialog_module = sys.modules["src.ui.features.settings.update_dialog"]
            if self._installer_paused:
                dialog_module.resume_installer(self._installer_process)
                self._installer_paused = False
                self.pause_button.setText("暂停安装")
                self._set_progress_message("安装器已继续运行。")
            else:
                dialog_module.pause_installer(self._installer_process)
                self._installer_paused = True
                self.pause_button.setText("继续安装")
                self._set_progress_message("安装器已暂停。")
        except Exception as exc:  # pragma: no cover - platform process state
            self._set_progress_message(f"无法控制安装器：{exc}", warning=True)
            self._set_pause_button(False)


    def _start_download(self) -> None:
        if self._worker is not None:
            return
        if not self._confirm_download_selection():
            return
        assets = self._selected_assets()
        if not assets:
            self._set_progress_message("请至少勾选一个下载内容。")
            return
        self.download_button.setEnabled(False)
        self.github_button.setEnabled(False)
        self._download_running = True
        self._sync_release_check_button()
        self._set_option_enabled(False)
        self._download_started = True
        self._pause_event.clear()
        self._stop_event.clear()
        self._installer_process = None
        self._installer_paused = False
        self.pause_button.setText("暂停下载")
        self.pause_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_percent.setText("0%")
        self.download_speed_label.setText("下载速度：0 B/s")
        self.download_size_label.setText("已下载：0 B / --")
        self._latest_downloaded = 0
        self._speed_baseline_downloaded = 0
        self.stop_button.setEnabled(True)
        self._download_speed_timer.start()
        self._set_progress_message("正在准备下载…")
        download_weights = _download_weights(
            self.program_checkbox.isChecked(), len(assets)
        )
        worker = Worker(
            "release_assets_download",
            lambda report: download_release_assets(
                assets,
                progress=_build_download_progress_reporter(report, download_weights),
                pause_event=self._pause_event,
                stop_event=self._stop_event,
            ),
            accepts_progress=True,
        )
        self._worker = worker
        worker.progress.connect(self._apply_progress)
        worker.progress_detail.connect(self._apply_download_detail)
        worker.finished_with_payload.connect(self._apply_download_result)
        worker.finished.connect(lambda: self._clear_worker(worker))
        worker.start()


    def _apply_download_detail(self, detail) -> None:
        _apply_download_detail(self, detail)


    def _set_pause_button(self, enabled: bool) -> None:
        self.pause_button.setEnabled(enabled)
        if not enabled:
            self.pause_button.setText("暂停")


    def _sync_release_check_button(self) -> None:
        if not hasattr(self, "refresh_button"):
            return
        self.refresh_button.setEnabled(
            not self._release_check_in_progress
            and not self._download_running
            and self._worker is None
        )


    def _apply_download_result(self, _kind: str, payload) -> None:
        self._download_running = False
        self._download_speed_timer.stop()
        self.stop_button.setEnabled(False)
        if isinstance(payload, dict) and payload.get("error"):
            cancelled = str(payload["error"]) == "下载已取消。"
            self._pause_event.clear()
            self._stop_event.clear()
            self._set_pause_button(False)
            self.progress_bar.setValue(0)
            self.progress_percent.setText("0%")
            self.download_speed_label.setText("下载速度：0 B/s")
            self.download_size_label.setText("已下载：0 B / --")
            self._latest_downloaded = 0
            self._speed_baseline_downloaded = 0
            self._set_progress_message(
                "下载已取消。" if cancelled else f"下载安装包失败：{payload['error']}",
                warning=not cancelled,
            )
            self.download_button.setEnabled(True)
            self.github_button.setEnabled(bool(self.result.release_url))
            self._set_option_enabled(True)
            return
        paths = tuple(Path(str(path)) for path in (payload or ()))
        program_path = next(
            (path for path in paths if path.name == self.result.installer_asset_name),
            None,
        )
        installer_error = ""
        if self.program_checkbox.isChecked():
            if program_path is None:
                installer_error = "下载结果中没有找到程序安装包。"
            else:
                try:
                    self._installer_process = launch_installer(program_path)
                except Exception as exc:  # pragma: no cover - platform launcher
                    installer_error = str(exc) or "系统拒绝启动安装包。"
        extra_path = next(
            (
                path
                for path in paths
                if path.name.casefold().startswith(
                    f"{variant_asset_prefix(self.result.variant).casefold()}_extraenv_"
                )
            ),
            None,
        )
        hot_install_started = False
        if (
            extra_path is not None
            and self.extra_environment_checkbox.isChecked()
            and not self.program_checkbox.isChecked()
        ):
            hot_install_started = self._hot_install_extra_environment(extra_path)
        self.progress_bar.setValue(100)
        self.progress_percent.setText("100%")
        self.download_speed_label.setText("下载速度：0 B/s")
        self._pause_event.clear()
        self._set_pause_button(False)
        names = "、".join(path.name for path in paths)
        if installer_error:
            self._set_progress_message(
                f"已下载：{names}，但安装包启动失败：{installer_error}",
                warning=True,
            )
            self.download_button.setEnabled(True)
            self.github_button.setEnabled(bool(self.result.release_url))
            self._set_option_enabled(True)
        elif program_path is not None:
            self._set_progress_message(f"已下载 {names}，安装包已启动。")
            if self._installer_process is not None:
                self.pause_button.setText("暂停安装")
                self.pause_button.setEnabled(True)
        elif hot_install_started:
            self._set_progress_message(f"已下载：{names}，附加环境包正在热安装。")
        else:
            self._set_progress_message(f"已下载：{names}。")


    def _set_progress_message(self, message: str, *, warning: bool = False) -> None:
        self.progress_message.setText(message)
        self.progress_message.setProperty("warning", warning)
        style = self.progress_message.style()
        style.unpolish(self.progress_message)
        style.polish(self.progress_message)


    def _clear_worker(self, worker: Worker) -> None:
        if self._worker is worker:
            self._worker = None
            self._sync_release_check_button()


    def _stop_download(self) -> None:
        if self._worker is None:
            return
        self._stop_event.set()
        self._pause_event.clear()
        self._download_speed_timer.stop()
        self.stop_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        self.download_speed_label.setText("下载速度：0 B/s")
        self._set_progress_message("正在取消下载…")


    def _request_release_check(self) -> None:
        if self._release_check_in_progress:
            return
        owner = self.parentWidget()
        context = getattr(owner, "context", None)
        run_background = getattr(context, "run_background", None)
        if not callable(run_background):
            self._set_progress_message("无法启动版本检测。", warning=True)
            return
        self._release_check_in_progress = True
        self._sync_release_check_button()
        self._set_progress_message("正在检测最新版本…")
        run_background(
            "release_check",
            lambda: check_latest_release(),
            receiver=owner,
        )


    def _apply_progress(self, message: str, value: int) -> None:
        if self._pause_event.is_set():
            return
        self.progress_bar.setValue(value)
        self.progress_percent.setText(f"{value}%")
        self._set_progress_message(message)


    def _update_download_speed(self) -> None:
        _update_download_speed(self)


__all__ = ['ReleaseUpdateDownloadMixin']
