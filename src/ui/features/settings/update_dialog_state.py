from __future__ import annotations

import re

from src.services.runtime.release_updates import ReleaseCheckResult
from src.services.runtime.variant import CPU_VARIANT, normalize_variant, variant_asset_prefix
from src.shared.qt import QFrame, QLabel, QVBoxLayout


def release_check_is_active(parent) -> bool:
    context = getattr(parent, "context", None)
    tasks = getattr(context, "tasks", None)
    is_active = getattr(tasks, "is_active", None)
    return bool(callable(is_active) and is_active("release_check"))


def apply_release_check_result(dialog, result: ReleaseCheckResult) -> None:
    dialog.result = result
    dialog.extra_environment_checkbox.setVisible(
        normalize_variant(result.variant) != CPU_VARIANT
    )
    dialog.base_environment_checkbox.setVisible(
        normalize_variant(result.variant) != CPU_VARIANT
    )
    dialog.current_version_label.setText(f"当前版本 {result.current_version}")
    if dialog.latest_version_label is not None:
        dialog.latest_version_label.setText(result.latest_version or "-")
    dialog.notes.setPlainText(result.release_notes or "暂无发布说明。")
    dialog._release_check_in_progress = False
    sync_environment_notice(dialog)
    if dialog._download_running:
        dialog._sync_release_check_button()
        return
    dialog.program_checkbox.setEnabled(bool(result.installer_asset_url))
    dialog.program_checkbox.setChecked(bool(result.installer_asset_url))
    dialog.base_environment_checkbox.setEnabled(
        normalize_variant(result.variant) != CPU_VARIANT
        and bool(result.installer_asset_url)
        and has_environment_asset(result, "baseenv")
    )
    dialog.base_environment_checkbox.setChecked(
        normalize_variant(result.variant) != CPU_VARIANT
        and bool(result.installer_asset_url)
        and has_environment_update(result, "baseenv")
    )
    dialog.extra_environment_checkbox.setEnabled(
        has_environment_asset(result, "extraenv")
    )
    dialog.extra_environment_checkbox.setChecked(False)
    dialog._sync_download_button()
    dialog._sync_release_check_button()
    if result.error:
        dialog._set_progress_message("版本检测失败，请稍后重试。", warning=True)
    else:
        dialog._set_progress_message("已刷新 GitHub Release 信息。")


def apply_download_detail(dialog, detail) -> None:
    if dialog._pause_event.is_set() or not isinstance(detail, dict):
        return
    downloaded = max(0, int(detail.get("downloaded") or 0))
    total = max(0, int(detail.get("total") or 0))
    dialog._latest_downloaded = downloaded
    total_text = _format_download_size(total) if total else "--"
    dialog.download_size_label.setText(
        f"已下载：{_format_download_size(downloaded)} / {total_text}"
    )


def update_download_speed(dialog) -> None:
    speed = max(0, dialog._latest_downloaded - dialog._speed_baseline_downloaded)
    dialog._speed_baseline_downloaded = dialog._latest_downloaded
    dialog.download_speed_label.setText(
        f"下载速度：{_format_download_size(speed)}/s"
    )


def build_download_progress_reporter(report, weights):
    state = {
        "index": -1,
        "completed_downloaded": 0,
        "completed_total": 0,
        "current_downloaded": 0,
        "current_total": 0,
    }

    def report_download_progress(name, index, count, downloaded, total):
        if index != state["index"]:
            if state["index"] >= 0:
                state["completed_downloaded"] += state["current_downloaded"]
                state["completed_total"] += state["current_total"]
            state["index"] = index
        state["current_downloaded"] = downloaded
        state["current_total"] = total
        report(
            f"正在下载{name}…",
            aggregate_download_percent(
                index,
                count,
                downloaded,
                total,
                weights=weights,
            ),
            {
                "downloaded": state["completed_downloaded"] + downloaded,
                "total": state["completed_total"] + total,
            },
        )

    return report_download_progress


def download_percent(downloaded: int, total: int) -> int:
    if total <= 0:
        return 0
    return max(0, min(100, int(downloaded * 100 / total)))


def download_weights(program_selected: bool, count: int) -> tuple[int, ...]:
    if count <= 0:
        return ()
    if program_selected and count == 2:
        return (20, 80)
    if program_selected and count == 3:
        return (10, 45, 45)
    share, remainder = divmod(100, count)
    return tuple(share + int(index < remainder) for index in range(count))


def aggregate_download_percent(
    index: int,
    count: int,
    downloaded: int,
    total: int,
    *,
    weights: tuple[int, ...] | None = None,
) -> int:
    current = download_percent(downloaded, total)
    resolved_weights = weights or download_weights(False, count)
    if not resolved_weights or index >= len(resolved_weights):
        return 0
    completed = sum(resolved_weights[:index])
    current_weight = resolved_weights[index] * current / 100
    return max(0, min(100, int(completed + current_weight)))


def _format_download_size(value: int) -> str:
    amount = float(max(0, value))
    units = ("B", "KB", "MB", "GB", "TB")
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(amount)} {unit}"
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return "0 B"


def build_environment_notice(result: ReleaseCheckResult) -> QFrame:
    notice = QFrame()
    notice.setObjectName("releaseEnvironmentNotice")
    notice_layout = QVBoxLayout(notice)
    notice_layout.setContentsMargins(12, 10, 12, 10)
    notice_layout.setSpacing(4)
    title = QLabel()
    title.setObjectName("releaseEnvironmentTitle")
    text = QLabel()
    text.setObjectName("releaseEnvironmentText")
    text.setWordWrap(True)
    if has_any_environment_update(result):
        title.setText("检测到环境包也有更新")
        text.setText("可在下方勾选环境包，与程序安装包一起下载。")
    else:
        title.setText("当前环境无附加包")
        text.setText("可在本界面选择性下载安装附加环境包。")
    notice_layout.addWidget(title)
    notice_layout.addWidget(text)
    return notice


def sync_environment_notice(dialog) -> None:
    if dialog.environment_notice is not None:
        dialog._main_layout.removeWidget(dialog.environment_notice)
        dialog.environment_notice.setParent(None)
        dialog.environment_notice.deleteLater()
        dialog.environment_notice = None
    if not (
        has_any_environment_update(dialog.result)
        or has_optional_extra_environment(dialog.result)
    ):
        return
    dialog.environment_notice = build_environment_notice(dialog.result)
    progress_index = dialog._main_layout.indexOf(dialog._progress_panel)
    dialog._main_layout.insertWidget(progress_index, dialog.environment_notice)


def find_environment_assets(
    result: ReleaseCheckResult,
    prefix: str,
) -> tuple[tuple[str, str], ...]:
    marker = variant_asset_prefix(result.variant).casefold()
    candidates = [
        (name, url)
        for name, url in zip(result.environment_asset_names, result.environment_asset_urls)
        if name.casefold().startswith(f"{marker}_{prefix.casefold()}_") and url
    ]
    if prefix.casefold() != "baseenv":
        return tuple(candidates[:1])

    volume_pattern = re.compile(
        rf"^(?P<stem>{re.escape(marker)}_BaseEnv_[0-9A-Za-z.-]+\.7z)\.(?P<part>[0-9]{{3}})$",
        re.IGNORECASE,
    )
    volumes = []
    for name, url in candidates:
        match = volume_pattern.fullmatch(name)
        if match is not None:
            volumes.append((int(match.group("part")), match.group("stem"), name, url))
    if volumes:
        stem = volumes[0][1]
        grouped = sorted((item for item in volumes if item[1] == stem), key=lambda item: item[0])
        expected = list(range(1, grouped[-1][0] + 1))
        if [item[0] for item in grouped] == expected and len(grouped) >= 1:
            return tuple((item[2], item[3]) for item in grouped)
        return ()
    return tuple(candidates[:1])


def find_environment_asset(
    result: ReleaseCheckResult,
    prefix: str,
) -> tuple[str, str] | None:
    assets = find_environment_assets(result, prefix)
    return assets[0] if assets else None


def has_environment_asset(result: ReleaseCheckResult, prefix: str) -> bool:
    return find_environment_asset(result, prefix) is not None


def has_environment_update(result: ReleaseCheckResult, prefix: str) -> bool:
    field = {
        "baseenv": "base_environment_update_available",
        "extraenv": "extra_environment_update_available",
    }.get(prefix)
    value = getattr(result, field, None) if field else None
    if value is None:
        return has_environment_asset(result, prefix)
    return bool(value)


def has_any_environment_update(result: ReleaseCheckResult) -> bool:
    return has_environment_update(result, "baseenv") or has_environment_update(
        result, "extraenv"
    )


def has_optional_extra_environment(result: ReleaseCheckResult) -> bool:
    return (
        has_environment_asset(result, "extraenv")
        and not has_environment_update(result, "extraenv")
        and not str(result.installed_extra_environment_version or "").strip()
    )


__all__ = [
    "apply_download_detail",
    "apply_release_check_result",
    "aggregate_download_percent",
    "build_download_progress_reporter",
    "download_percent",
    "download_weights",
    "build_environment_notice",
    "find_environment_asset",
    "find_environment_assets",
    "has_any_environment_update",
    "has_environment_asset",
    "has_environment_update",
    "has_optional_extra_environment",
    "release_check_is_active",
    "sync_environment_notice",
    "update_download_speed",
]
