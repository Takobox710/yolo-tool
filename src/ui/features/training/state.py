from __future__ import annotations

from pathlib import Path

from src.services.runtime import system_status, torch_cuda_summary
from src.services.settings import build_default_settings
from src.services.training import (
    build_train_command,
    default_training_device,
    format_training_image_size,
    infer_task_mode_from_model,
    resolve_training_model_reference,
    training_device_options,
)


def refresh_train_status(page):
    page.context.run_background(
        "train_status",
        lambda: {
            "status": system_status(),
            "cuda": torch_cuda_summary(use_subprocess=True),
        },
    )


def apply_train_status(page, payload):
    status = payload["status"]
    cuda = payload["cuda"]
    page.metric_labels["gpu"].setText(
        f"{page.short_gpu_name(status.get('gpu') or cuda.get('gpu', '待检测'))} · {status.get('gpu_usage', '待检测')}"
    )
    page.metric_labels["vram"].setText(status.get("vram", "待检测"))
    page.metric_labels["cpu"].setText(status.get("cpu", "待检测"))
    page.metric_labels["memory"].setText(status.get("memory", "待检测"))
    apply_detected_device_options(page, cuda)


def current_device_value(page) -> str:
    value = page.device_combo.currentData()
    return str(value) if value is not None else page.device_combo.currentText()


def apply_detected_device_options(page, cuda_summary: dict | None) -> None:
    """按检测到的 CUDA GPU 数量重建训练设备选项，并修复无效的已保存设备值。"""
    summary = dict(cuda_summary or {})
    available = str(summary.get("available", "")).strip().lower() == "true"
    try:
        gpu_count = max(0, int(summary.get("count") or 0))
    except (TypeError, ValueError):
        gpu_count = 0
    if str(summary.get("gpu") or "") in {"", "不可用", "未知", "未安装"}:
        available = False
        gpu_count = 0
    option_pairs = training_device_options(
        cuda_available=available, gpu_count=gpu_count
    )
    raw_values = {value for _label, value in option_pairs}
    combo = page.device_combo
    existing = [
        (combo.itemText(index), combo.itemData(index))
        for index in range(combo.count())
    ]
    current = current_device_value(page)
    changed = False
    if existing != option_pairs:
        if current not in raw_values:
            current = default_training_device(
                cuda_available=available, gpu_count=gpu_count
            )
        combo.blockSignals(True)
        combo.clear()
        for label, value in option_pairs:
            combo.addItem(label, value)
        index = combo.findData(current)
        combo.setCurrentIndex(index if index >= 0 else 0)
        combo.blockSignals(False)
        changed = True
    elif current not in raw_values:
        current = default_training_device(
            cuda_available=available, gpu_count=gpu_count
        )
        index = combo.findData(current)
        combo.setCurrentIndex(index if index >= 0 else 0)
        changed = True
    if changed or getattr(page.context.settings.training, "device", "") != current:
        page.context.settings.training.device = current
        page.save_settings()
        refresh_command_preview(page)


def collect_config(page):
    config = {}
    config["data"] = (
        page.resolve_path_text(page.edits["data"]) if page.edits["data"] else ""
    )
    config["model_yaml"] = (
        page.resolve_path_text(page.edits["model_yaml"])
        if page.edits["model_yaml"]
        else ""
    )
    config["project"] = (
        page.resolve_path_text(page.edits["project"])
        if page.edits["project"]
        else ""
    )
    config["lr"] = page.edits["lr"].text() if page.edits.get("lr") else "0.001"
    config["epochs"] = (
        page.edits["epochs"].text() if page.edits.get("epochs") else "500"
    )
    config["patience"] = (
        page.edits["patience"].text() if page.edits.get("patience") else "100"
    )
    config["workers"] = (
        page.edits["workers"].text() if page.edits.get("workers") else "2"
    )
    config["batch"] = (
        page.edits["batch"].text() if page.edits.get("batch") else "16"
    )
    config["imgsz"] = (
        page.imgsz_combo.currentText() if hasattr(page, "imgsz_combo") else "640"
    )
    config["device"] = current_device_value(page)
    selected_model = page._resolve_model_reference(page.pretrained_combo.currentText())
    config["base_model"] = selected_model
    config["pretrained"] = selected_model
    config["optimizer"] = page.optimizer_combo.currentText()
    for key in ("epochs", "patience", "workers", "batch"):
        try:
            config[key] = int(config[key])
        except (ValueError, TypeError):
            config[key] = int(getattr(page.context.settings.training, key))
    config["imgsz"] = format_training_image_size(config["imgsz"])
    try:
        config["lr"] = float(config["lr"])
    except (ValueError, TypeError):
        config["lr"] = float(page.context.settings.training.lr)
    config["task_mode"] = infer_task_mode_from_model(
        config.get("model_yaml") or config.get("base_model") or config.get("pretrained")
    )
    for key, check in page.checks.items():
        if key == "hsv_h":
            continue
        config[key] = (
            getattr(page.context.settings.training, key)
            if check.isChecked()
            else 0
        )
    hsv_enabled = page.checks["hsv_h"].isChecked()
    config["hsv_h"] = (
        page.context.settings.training.hsv_h
        if hsv_enabled
        else 0
    )
    config["hsv_s"] = (
        page.context.settings.training.hsv_s
        if hsv_enabled
        else 0
    )
    config["hsv_v"] = (
        page.context.settings.training.hsv_v
        if hsv_enabled
        else 0
    )
    return config


def models_dir(page) -> Path:
    return Path(page.context.settings.paths.models_dir)


def default_training_value(page, key: str):
    return getattr(build_default_settings(page.project_root()).training, key, 0)


def save_training_settings(page, config: dict):
    training = page.context.settings.training
    for key in (
        "data",
        "model_yaml",
        "project",
        "lr",
        "epochs",
        "patience",
        "workers",
        "batch",
        "imgsz",
        "device",
        "base_model",
        "pretrained",
        "optimizer",
        "mosaic",
        "fliplr",
        "flipud",
        "mixup",
        "scale",
        "translate",
        "degrees",
        "hsv_h",
        "hsv_s",
        "hsv_v",
    ):
        if key in config:
            setattr(training, key, config[key])
    page.save_settings()


def connect_training_persistence(page):
    watched_edits = (
        ("data", page.edits["data"]),
        ("model_yaml", page.edits["model_yaml"]),
        ("project", page.edits["project"]),
        ("lr", page.edits["lr"]),
        ("epochs", page.edits["epochs"]),
        ("patience", page.edits["patience"]),
        ("workers", page.edits["workers"]),
        ("batch", page.edits["batch"]),
    )
    for key, edit in watched_edits:
        edit.textChanged.connect(
            lambda _text, setting_key=key: persist_training_text(page, setting_key)
        )
    page.pretrained_combo.currentTextChanged.connect(
        lambda _value: persist_model_selection(page)
    )
    page.optimizer_combo.currentTextChanged.connect(
        lambda value: persist_training_value(page, "optimizer", value)
    )
    page.imgsz_combo.currentTextChanged.connect(
        lambda value: persist_training_image_size(page, value)
    )
    page.device_combo.currentTextChanged.connect(
        lambda _value: persist_training_device(page)
    )
    for key, check in page.checks.items():
        check.toggled.connect(
            lambda _checked, setting_key=key: persist_augmentation(page, setting_key)
        )


def persist_training_text(page, key: str):
    edit = page.edits.get(key)
    if edit is None:
        return
    value = (
        page.resolve_path_text(edit)
        if key in {"data", "model_yaml", "project"}
        else edit.text()
    )
    setattr(page.context.settings.training, key, value)
    page.save_settings()
    refresh_command_preview(page)


def persist_training_value(page, key: str, value):
    setattr(page.context.settings.training, key, value)
    page.save_settings()
    refresh_command_preview(page)


def persist_training_device(page):
    persist_training_value(page, "device", current_device_value(page))


def persist_training_image_size(page, value: str):
    try:
        normalized = format_training_image_size(value)
    except ValueError:
        return
    persist_training_value(page, "imgsz", normalized)


def persist_model_selection(page):
    selected_model = page._resolve_model_reference(page.pretrained_combo.currentText())
    training = page.context.settings.training
    training.base_model = selected_model
    training.pretrained = selected_model
    page.save_settings()
    refresh_command_preview(page)


def persist_augmentation(page, key: str):
    training = page.context.settings.training
    if key == "hsv_h":
        enabled = page.checks[key].isChecked()
        training.hsv_h = (
            training.hsv_h
            if enabled
            else 0
        )
        training.hsv_s = (
            training.hsv_s
            if enabled
            else 0
        )
        training.hsv_v = (
            training.hsv_v
            if enabled
            else 0
        )
    else:
        setattr(training, key, (
            getattr(training, key)
            if page.checks[key].isChecked()
            else 0
        ))
    page.save_settings()
    refresh_command_preview(page)


def resolve_model_reference(page, model_text: str) -> str:
    return resolve_training_model_reference(
        model_text,
        Path(page.context.settings.project.root),
    )


def refresh_command_preview(page):
    try:
        command = build_train_command(page.collect_config())
    except ValueError as exc:
        page.log.setPlainText(f"训练参数无效：{exc}")
        return
    page.log.setPlainText(" ".join(command) + "\n等待开始训练...")


def normalize_command_model_targets(page, command: list[str]) -> list[str]:
    models_dir_path = page._models_dir()
    models_dir_path.mkdir(parents=True, exist_ok=True)
    normalized: list[str] = []
    for part in command:
        if not part.startswith(("model=", "pretrained=")):
            normalized.append(part)
            continue
        key, value = part.split("=", 1)
        if not value:
            normalized.append(part)
            continue
        path = Path(value)
        if path.suffix.lower() == ".pt" and not path.is_absolute():
            value = str((models_dir_path / path.name).resolve())
        normalized.append(f"{key}={value}")
    return normalized
