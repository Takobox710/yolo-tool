from __future__ import annotations

from pathlib import Path

from src.services.runtime import (
    application_version,
    dependency_versions,
    python_version,
    torch_cuda_summary,
)
from src.services.settings import build_default_settings
from src.shared.qt import QMessageBox, Qt


def build_control_widgets(page) -> list:
    widgets = []
    dist_box, page.distribution_mode_check = page.checkbox_with_help(
        "多类别分布模式",
        page.app.settings.get("features", {}).get("distribution_multi_class_mode", False),
        help_text="开启后首页按多类别模式展示类别分布；顶部只显示总图片数，柱状图按各类别分别统计。",
    )
    page.distribution_mode_check.stateChanged.connect(page._toggle_distribution_mode)
    widgets.append(dist_box)

    cmd_box, page.cmd_dialog_check = page.checkbox_with_help(
        "训练前显示自定义命令框",
        page.app.settings.get("features", {}).get("custom_command_dialog", True),
        help_text="开启后点击开始训练会先弹出自定义命令框；关闭后直接按当前配置启动训练。",
    )
    page.cmd_dialog_check.setChecked(
        page.app.settings.get("features", {}).get("custom_command_dialog", True)
    )
    page.cmd_dialog_check.stateChanged.connect(page._toggle_custom_cmd)
    widgets.append(cmd_box)

    help_box, page.help_icon_check = page.checkbox_with_help(
        "显示配置解释符号",
        page.app.settings.get("features", {}).get("show_help_icons", True),
        help_text="开启后在配置名称后显示 ⓘ；关闭时只隐藏符号，鼠标悬停字段名称本身仍可查看解释。",
    )
    page.help_icon_check.setChecked(
        page.app.settings.get("features", {}).get("show_help_icons", True)
    )
    page.help_icon_check.stateChanged.connect(page._toggle_help_icons)
    widgets.append(help_box)

    model_box, page.show_last_models_check = page.checkbox_with_help(
        "模型验证显示 last",
        page.app.settings.get("features", {}).get("show_last_training_models", False),
        help_text="开启后模型验证页的模型列表会额外显示各训练目录下的 last.pt；关闭时只显示 best.pt。",
    )
    page.show_last_models_check.setChecked(
        page.app.settings.get("features", {}).get("show_last_training_models", False)
    )
    page.show_last_models_check.stateChanged.connect(page._toggle_show_last_training_models)
    widgets.append(model_box)
    return widgets


def toggle_custom_cmd(page, state):
    page.app.settings.setdefault("features", {})["custom_command_dialog"] = (
        state == Qt.CheckState.Checked.value
    )
    page.app.settings_service.save(page.app.settings)


def toggle_distribution_mode(page, state):
    page.app.settings.setdefault("features", {})["distribution_multi_class_mode"] = (
        state == Qt.CheckState.Checked.value
    )
    page.app.settings_service.save(page.app.settings)
    home_page = page.app.pages.get("home") if hasattr(page.app, "pages") else None
    target = getattr(home_page, "inner_page", home_page)
    hook = getattr(target, "on_show", None)
    if hook:
        hook()


def toggle_help_icons(page, state):
    page.app.settings.setdefault("features", {})["show_help_icons"] = (
        state == Qt.CheckState.Checked.value
    )
    page.app.settings_service.save(page.app.settings)
    refresh = getattr(page.app, "refresh_help_icon_visibility", None)
    if refresh:
        refresh()
    else:
        page.refresh_help_icon_visibility()


def toggle_show_last_training_models(page, state):
    page.app.settings.setdefault("features", {})["show_last_training_models"] = (
        state == Qt.CheckState.Checked.value
    )
    page.app.settings_service.save(page.app.settings)
    refresh = getattr(page.app, "refresh_validation_model_options", None)
    if refresh:
        refresh()
        return
    pages = getattr(page.app, "pages", {}) or {}
    validate_page = pages.get("validate") if isinstance(pages, dict) else None
    target = getattr(validate_page, "inner_page", validate_page)
    hook = getattr(target, "refresh_model_choices", None)
    if hook:
        hook()


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
    reset = getattr(page.app, "reset_project_settings", None)
    if reset:
        reset("settings")
        return
    reset_settings = getattr(page.app.settings_service, "reset_to_defaults", None)
    if reset_settings:
        page.app.settings = reset_settings()
    else:
        project_root = Path(page.app.settings["project"]["root"])
        page.app.settings = build_default_settings(project_root)
        page.app.settings_service.save(page.app.settings)
    page.cmd_dialog_check.setChecked(
        page.app.settings.get("features", {}).get("custom_command_dialog", True)
    )
    page.distribution_mode_check.setChecked(
        page.app.settings.get("features", {}).get("distribution_multi_class_mode", False)
    )
    page.help_icon_check.setChecked(
        page.app.settings.get("features", {}).get("show_help_icons", True)
    )
    page.show_last_models_check.setChecked(
        page.app.settings.get("features", {}).get("show_last_training_models", False)
    )
    refresh = getattr(page.app, "refresh_help_icon_visibility", None)
    if refresh:
        refresh()
    QMessageBox.information(page, "恢复默认设置", "当前项目设置已恢复为默认值。")


def auto_refresh(page):
    page._refresh_count += 1
    page.app.run_background("env_auto", lambda: load_env_payload(page))


def on_show(page):
    if not page._auto_refresh_timer.isActive():
        page._auto_refresh_timer.start()
    for label in page.status_cards:
        page.set_status_card(label, "检测中...")
    page.log.setPlainText(page.program_log_text())
    page.app.run_background("env", lambda: load_env_payload(page))


def load_env_payload(page):
    return {
        "python": python_version(),
        "dependencies": dependency_versions(),
        "cuda": torch_cuda_summary(use_subprocess=True),
        "app_version": application_version(),
        "settings": page.app.settings,
    }


def apply_env_data(page, payload):
    python_text = payload.get("python") or "未知"
    dependencies = payload.get("dependencies") or {}
    cuda = payload.get("cuda") or {}
    torch_text = format_torch_status(cuda)

    page.set_status_card("Python", f"{python_text}：可用")
    page.set_status_card("Torch", torch_text)
    page.set_status_card("Ultralytics", format_dependency_status(dependencies, "Ultralytics"))
    page.set_status_card("PySide6", format_dependency_status(dependencies, "PySide6"))
    page.set_status_card("OpenCV", format_dependency_status(dependencies, "OpenCV"))
    page.set_status_card("Pillow", format_dependency_status(dependencies, "Pillow"))
    page.set_status_card("psutil", format_dependency_status(dependencies, "psutil"))
    page.set_status_card("程序版本", payload.get("app_version", "未知"))


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
