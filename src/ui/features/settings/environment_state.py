from __future__ import annotations

from pathlib import Path

from src.services.runtime import application_version, dependency_versions, python_version, torch_cuda_summary
from src.services.settings import build_default_settings
from src.shared.qt import QMessageBox, Qt


def build_control_widgets(page) -> list:
    widgets = []
    controls = (
        ("distribution_mode_check", "多类别分布模式", "distribution_multi_class_mode", page._toggle_distribution_mode, "开启后首页按多类别模式展示类别分布；顶部只显示总图片数，柱状图按各类别分别统计。"),
        ("cmd_dialog_check", "训练前显示自定义命令框", "custom_command_dialog", page._toggle_custom_cmd, "开启后点击开始训练会先弹出自定义命令框；关闭后直接按当前配置启动训练。"),
        ("help_icon_check", "显示配置解释符号", "show_help_icons", page._toggle_help_icons, "开启后在配置名称后显示 ⓘ；关闭时只隐藏符号，鼠标悬停字段名称本身仍可查看解释。"),
        ("show_last_models_check", "模型验证显示 last", "show_last_training_models", page._toggle_show_last_training_models, "开启后模型验证页的模型列表会额外显示各训练目录下的 last.pt；关闭时只显示 best.pt。"),
    )
    for attribute, text, setting, callback, help_text in controls:
        box, check = page.checkbox_with_help(
            text,
            getattr(page.context.settings.features, setting),
            help_text=help_text,
        )
        setattr(page, attribute, check)
        check.setChecked(getattr(page.context.settings.features, setting))
        check.stateChanged.connect(callback)
        widgets.append(box)
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
        page, "恢复默认设置", "将当前项目的设置恢复为默认值？当前项目文件夹路径会保留不变。",
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
    for name in ("cmd_dialog_check", "distribution_mode_check", "help_icon_check", "show_last_models_check"):
        check = getattr(page, name)
        setting = {
            "cmd_dialog_check": "custom_command_dialog",
            "distribution_mode_check": "distribution_multi_class_mode",
            "help_icon_check": "show_help_icons",
            "show_last_models_check": "show_last_training_models",
        }[name]
        check.setChecked(getattr(page.context.settings.features, setting))
    refresh = getattr(page.context, "refresh_help_icon_visibility", None)
    if refresh:
        refresh()
    QMessageBox.information(page, "恢复默认设置", "当前项目设置已恢复为默认值。")


def auto_refresh(page):
    page._refresh_count += 1
    page.context.run_background("env_auto", lambda: load_env_payload(page))


def load_env_payload(page):
    return {
        "python": python_version(),
        "dependencies": dependency_versions(),
        "cuda": torch_cuda_summary(use_subprocess=True),
        "app_version": application_version(),
        "settings": page.context.settings,
    }


def apply_env_data(page, payload):
    dependencies = payload.get("dependencies") or {}
    cuda = payload.get("cuda") or {}
    page.set_status_card("Python", f"{payload.get('python') or '未知'}：可用")
    page.set_status_card("Torch", format_torch_status(cuda))
    for label in ("Ultralytics", "ONNX", "OpenCV", "Pillow", "TensorRT"):
        page.set_status_card(label, format_dependency_status(dependencies, label))
    page.set_status_card("程序版本", payload.get("app_version", "未知"))


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


__all__ = [
    "apply_env_data", "auto_refresh", "build_control_widgets", "format_dependency_status",
    "format_torch_status", "load_env_payload", "reset_defaults", "toggle_custom_cmd",
    "toggle_distribution_mode", "toggle_help_icons", "toggle_show_last_training_models",
]
