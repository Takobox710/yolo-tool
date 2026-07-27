from __future__ import annotations

from pathlib import Path

from src.services.runtime import (
    application_version,
    dependency_versions,
    python_version,
    sanitize_terminal_line,
    torch_cuda_summary,
)
from src.services.runtime.release_updates import ReleaseCheckResult, check_latest_release
from src.services.settings import build_default_settings
from src.shared.qt import QMessageBox, Qt


def build_control_widgets(page) -> list:
    widgets = []
    dist_box, page.distribution_mode_check = page.checkbox_with_help(
        "多类别分布模式",
        page.context.settings.features.distribution_multi_class_mode,
        help_text="开启后首页按多类别模式展示类别分布；顶部只显示总图片数，柱状图按各类别分别统计。",
    )
    page.distribution_mode_check.stateChanged.connect(page._toggle_distribution_mode)
    widgets.append(dist_box)

    cmd_box, page.cmd_dialog_check = page.checkbox_with_help(
        "训练前显示自定义命令框",
        page.context.settings.features.custom_command_dialog,
        help_text="开启后点击开始训练会先弹出自定义命令框；关闭后直接按当前配置启动训练。",
    )
    page.cmd_dialog_check.setChecked(
        page.context.settings.features.custom_command_dialog
    )
    page.cmd_dialog_check.stateChanged.connect(page._toggle_custom_cmd)
    widgets.append(cmd_box)

    help_box, page.help_icon_check = page.checkbox_with_help(
        "显示配置解释符号",
        page.context.settings.features.show_help_icons,
        help_text="开启后在配置名称后显示 ⓘ；关闭时只隐藏符号，鼠标悬停字段名称本身仍可查看解释。",
    )
    page.help_icon_check.setChecked(
        page.context.settings.features.show_help_icons
    )
    page.help_icon_check.stateChanged.connect(page._toggle_help_icons)
    widgets.append(help_box)

    model_box, page.show_last_models_check = page.checkbox_with_help(
        "模型验证显示 last",
        page.context.settings.features.show_last_training_models,
        help_text="开启后模型验证页的模型列表会额外显示各训练目录下的 last.pt；关闭时只显示 best.pt。",
    )
    page.show_last_models_check.setChecked(
        page.context.settings.features.show_last_training_models
    )
    page.show_last_models_check.stateChanged.connect(page._toggle_show_last_training_models)
    widgets.append(model_box)
    return widgets


def toggle_custom_cmd(page, state):
    page.context.settings.features.custom_command_dialog = state == Qt.CheckState.Checked.value
    page.save_settings()


def toggle_distribution_mode(page, state):
    page.context.settings.features.distribution_multi_class_mode = state == Qt.CheckState.Checked.value
    page.save_settings()


def toggle_help_icons(page, state):
    page.context.settings.features.show_help_icons = state == Qt.CheckState.Checked.value
    page.save_settings()
    page.context.refresh_help_icons()


def toggle_show_last_training_models(page, state):
    page.context.settings.features.show_last_training_models = state == Qt.CheckState.Checked.value
    page.save_settings()
    page.context.refresh_validation_models()


def reset_defaults(page):
    answer = QMessageBox.question(
        page,
        "恢复默认设置",
        "将当前项目的设置恢复为默认值？当前项目文件夹路径会保留不变。",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if answer != QMessageBox.StandardButton.Yes:
        return
    reset = getattr(page.context, "reset_project_settings", None)
    if reset:
        reset("settings")
        return
    reset_settings = getattr(page.context.settings_service, "reset_to_defaults", None)
    if reset_settings:
        page.context.settings = reset_settings()
    else:
        project_root = Path(page.context.settings.project.root)
        page.context.settings = build_default_settings(project_root)
        page.context.settings_service.save(page.context.settings)
    page.cmd_dialog_check.setChecked(
        page.context.settings.features.custom_command_dialog
    )
    page.distribution_mode_check.setChecked(
        page.context.settings.features.distribution_multi_class_mode
    )
    page.help_icon_check.setChecked(
        page.context.settings.features.show_help_icons
    )
    page.show_last_models_check.setChecked(
        page.context.settings.features.show_last_training_models
    )
    refresh = getattr(page.context, "refresh_help_icon_visibility", None)
    if refresh:
        refresh()
    QMessageBox.information(page, "恢复默认设置", "当前项目设置已恢复为默认值。")


def auto_refresh(page):
    page._refresh_count += 1
    page.context.run_background("env_auto", lambda: load_env_payload(page))


def on_show(page):
    if not page._auto_refresh_timer.isActive():
        page._auto_refresh_timer.start()
    for label in page.status_cards:
        page.set_status_card(label, "检测中...")
    page.log.setPlainText(page.program_log_text())
    page.context.run_background("env", lambda: load_env_payload(page))
    if not page.context.release_check_started:
        page.context.release_check_started = True
        page.context.run_background(
            "release_check",
            lambda: check_latest_release(),
            receiver=page,
        )


def load_env_payload(page):
    return {
        "python": python_version(),
        "dependencies": dependency_versions(),
        "cuda": torch_cuda_summary(use_subprocess=True),
        "app_version": application_version(),
        "settings": page.context.settings,
    }


def apply_env_data(page, payload):
    python_text = payload.get("python") or "未知"
    dependencies = payload.get("dependencies") or {}
    cuda = payload.get("cuda") or {}
    torch_text = format_torch_status(cuda)

    page.set_status_card("Python", f"{python_text}：可用")
    page.set_status_card("Torch", torch_text)
    page.set_status_card("Ultralytics", format_dependency_status(dependencies, "Ultralytics"))
    page.set_status_card("ONNX", format_dependency_status(dependencies, "ONNX"))
    page.set_status_card("OpenCV", format_dependency_status(dependencies, "OpenCV"))
    page.set_status_card("Pillow", format_dependency_status(dependencies, "Pillow"))
    page.set_status_card("TensorRT", format_dependency_status(dependencies, "TensorRT"))
    page.set_status_card("程序版本", payload.get("app_version", "未知"))


def apply_release_check(page, payload) -> None:
    if isinstance(payload, dict):
        environment_assets = payload.get("environment_asset_names") or ()
        if isinstance(environment_assets, str):
            environment_assets = (environment_assets,)
        environment_urls = payload.get("environment_asset_urls") or ()
        if isinstance(environment_urls, str):
            environment_urls = (environment_urls,)
        result = ReleaseCheckResult(
            current_version=str(payload.get("current_version") or ""),
            latest_version=str(payload.get("latest_version") or ""),
            release_url=str(payload.get("release_url") or ""),
            release_notes=str(payload.get("release_notes") or ""),
            installer_asset_name=str(payload.get("installer_asset_name") or ""),
            installer_asset_url=str(payload.get("installer_asset_url") or ""),
            environment_asset_names=tuple(
                str(item)
                for item in environment_assets
                if str(item)
            ),
            environment_asset_urls=tuple(
                str(item)
                for item in environment_urls
                if str(item)
            ),
            update_available=bool(payload.get("update_available")),
            error=str(payload.get("error") or ""),
        )
    elif isinstance(payload, ReleaseCheckResult):
        result = payload
    else:
        return
    page.release_check_result = result
    page.upgrade_indicator.setVisible(result.update_available)
    if result.update_available:
        page.upgrade_indicator.setToolTip(
            f"查看版本更新：发现新版本 {result.latest_version}，当前版本 {result.current_version}"
        )
    else:
        page.upgrade_indicator.setToolTip("查看版本更新")
    _append_release_notes(page, result)
    page.release_check_toast.show_result(result)


def open_release_update_dialog(page) -> None:
    result = getattr(page, "release_check_result", None)
    if not isinstance(result, ReleaseCheckResult):
        version = application_version()
        result = ReleaseCheckResult(
            current_version=version,
            latest_version=version,
            release_notes="正在获取 GitHub Release 信息，请稍后再试。",
        )
    from src.ui.features.settings.update_dialog import ReleaseUpdateDialog

    dialog = ReleaseUpdateDialog(page, result)
    page.release_update_dialog = dialog
    dialog.exec()
    if getattr(page, "release_update_dialog", None) is dialog:
        page.release_update_dialog = None


def _append_release_notes(page, result: ReleaseCheckResult) -> None:
    if not result.update_available:
        return
    marker = f"{result.latest_version} 更新内容："
    if marker in page.log.toPlainText():
        return
    notes = "\n".join(
        cleaned
        for line in str(result.release_notes or "").splitlines()
        if (cleaned := sanitize_terminal_line(line).strip())
    )
    if not notes:
        notes = "暂无发布说明。"
    entry = (
        f"发现新版本 {result.latest_version}，当前版本 {result.current_version}。\n"
        f"{marker}\n{notes}"
    )
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
        return
    page.log.append(entry)


def format_dependency_status(dependencies: dict[str, str], label: str) -> str:
    version = str(dependencies.get(label, "未安装"))
    status = "可用" if version not in {"", "未安装"} else "不可用"
    return f"{version}：{status}"


def format_torch_status(cuda: dict[str, str]) -> str:
    torch_version = str(cuda.get("torch", "未安装"))
    cuda_version = str(cuda.get("cuda", "未知"))
    if torch_version in {"", "未安装", "未知"}:
        return f"{torch_version}：不可用"
    if cuda_version in {"", "None", "未知"}:
        return f"{torch_version}：CUDA不可用"
    return f"{torch_version}：可用"
