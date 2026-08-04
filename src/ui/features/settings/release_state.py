from __future__ import annotations

from src.services.runtime import application_version, sanitize_terminal_line
from src.services.runtime.release_updates import ReleaseCheckResult


def apply_release_check(page, payload) -> None:
    if isinstance(payload, dict):
        names = payload.get("environment_asset_names") or ()
        urls = payload.get("environment_asset_urls") or ()
        if isinstance(names, str):
            names = (names,)
        if isinstance(urls, str):
            urls = (urls,)
        result = ReleaseCheckResult(
            current_version=str(payload.get("current_version") or ""),
            variant=str(payload.get("variant") or "gpu"),
            latest_version=str(payload.get("latest_version") or ""),
            release_url=str(payload.get("release_url") or ""),
            release_notes=str(payload.get("release_notes") or ""),
            installer_asset_name=str(payload.get("installer_asset_name") or ""),
            installer_asset_url=str(payload.get("installer_asset_url") or ""),
            environment_asset_names=tuple(str(item) for item in names if str(item)),
            environment_asset_urls=tuple(str(item) for item in urls if str(item)),
            base_environment_version=str(payload.get("base_environment_version") or ""),
            extra_environment_version=str(payload.get("extra_environment_version") or ""),
            installed_base_environment_version=str(payload.get("installed_base_environment_version") or ""),
            installed_extra_environment_version=str(payload.get("installed_extra_environment_version") or ""),
            base_environment_update_available=_optional_bool(payload, "base_environment_update_available"),
            extra_environment_update_available=_optional_bool(payload, "extra_environment_update_available"),
            update_available=bool(payload.get("update_available")),
            error=str(payload.get("error") or ""),
        )
    elif isinstance(payload, ReleaseCheckResult):
        result = payload
    else:
        return
    page.release_check_result = result
    dialog = getattr(page, "release_update_dialog", None)
    refresh_dialog = getattr(dialog, "apply_release_check_result", None)
    if callable(refresh_dialog):
        refresh_dialog(result)
    page.upgrade_indicator.setVisible(result.update_available)
    page.upgrade_indicator.setToolTip(
        f"查看版本更新：发现新版本 {result.latest_version}，当前版本 {result.current_version}"
        if result.update_available else "查看版本更新"
    )
    _append_release_notes(page, result)
    page.release_check_toast.show_result(result)


def open_release_update_dialog(page) -> None:
    existing = getattr(page, "release_update_dialog", None)
    if existing is not None:
        existing.show()
        existing.raise_()
        existing.activateWindow()
        return
    result = getattr(page, "release_check_result", None)
    if not isinstance(result, ReleaseCheckResult):
        version = application_version()
        result = ReleaseCheckResult(current_version=version, latest_version=version, release_notes="正在获取 GitHub Release 信息，请稍后再试。")
    from src.ui.features.settings.update_dialog import ReleaseUpdateDialog

    # Own the top-level dialog by the workbench window.  Passing the stacked
    # settings page as the native owner can make Windows briefly expose an
    # unpainted transient window while Qt promotes the page to a top-level
    # window.
    owner = page.window()
    dialog = ReleaseUpdateDialog(owner if owner is not page else page, result)
    page.release_update_dialog = dialog

    def clear_dialog(_result=0):
        if getattr(page, "release_update_dialog", None) is dialog:
            page.release_update_dialog = None
        dialog.deleteLater()

    dialog.finished.connect(clear_dialog)
    dialog.show()
    dialog.raise_()
    dialog.activateWindow()


def _append_release_notes(page, result: ReleaseCheckResult) -> None:
    if not result.update_available:
        return
    marker = f"{result.latest_version} 更新内容："
    if marker in page.log.toPlainText():
        return
    notes = "\n".join(
        cleaned for line in str(result.release_notes or "").splitlines()
        if (cleaned := sanitize_terminal_line(line).strip())
    ) or "暂无发布说明。"
    entry = f"发现新版本 {result.latest_version}，当前版本 {result.current_version}。\n{marker}\n{notes}"
    append_log = getattr(page.context, "append_program_log", None)
    if not callable(append_log):
        append_program_log_entry(page, entry)
        return
    before = page.log.toPlainText()
    append_log(entry)
    if page.log.toPlainText() == before:
        append_program_log_entry(page, entry)


def append_program_log_entry(page, entry: str) -> None:
    current = page.log.toPlainText().strip()
    if not current or current == "等待程序日志...":
        page.log.setPlainText(entry)
    else:
        page.log.append(entry)


def _optional_bool(payload: dict, key: str) -> bool | None:
    value = payload.get(key)
    return None if value is None else bool(value)


__all__ = [
    "_optional_bool", "append_program_log_entry", "apply_release_check",
    "open_release_update_dialog",
]
