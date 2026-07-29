"""Settings dataclass compatibility exports and serialization validation."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any, get_args, get_origin, get_type_hints

from src.services.settings.types import (
    AiPrelabelSettings,
    AnnotationSettings,
    AppSettings,
    ConversionSettings,
    DatasetSettings,
    FeatureSettings,
    ImageResizeSettings,
    LineToObbSettings,
    ModelExportSettings,
    PathSettings,
    ProjectSettings,
    RenameSettings,
    SamAssistSettings,
    SettingsIssue,
    SettingsLoadResult,
    SplitRatios,
    TaskSettings,
    TrainingSettings,
    UiSettings,
    ValidationSettings,
)


def settings_to_dict(settings: AppSettings) -> dict[str, Any]:
    return _dataclass_to_dict(settings)


def settings_from_dict(payload: dict[str, Any], defaults: AppSettings) -> tuple[AppSettings, tuple[SettingsIssue, ...]]:
    issues: list[SettingsIssue] = []
    result = _coerce_dataclass(AppSettings, payload, defaults, "", issues)
    return result, tuple(issues)


def _dataclass_to_dict(value: Any) -> Any:
    if is_dataclass(value):
        return {field.name: _dataclass_to_dict(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, list):
        return [_dataclass_to_dict(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _dataclass_to_dict(item) for key, item in value.items()}
    return value


def _coerce_dataclass(cls: type, payload: Any, defaults: Any, prefix: str, issues: list[SettingsIssue]) -> Any:
    if not isinstance(payload, dict):
        issues.append(SettingsIssue(prefix or "settings", "必须是对象，已恢复默认值"))
        payload = {}
    known = {field.name for field in fields(cls)}
    for key in payload:
        if key not in known:
            issues.append(SettingsIssue(_join(prefix, key), "未知设置字段，已忽略"))
    hints = get_type_hints(cls)
    values: dict[str, Any] = {}
    for field in fields(cls):
        path = _join(prefix, field.name)
        fallback = getattr(defaults, field.name)
        raw = payload.get(field.name, fallback)
        values[field.name] = _coerce_value(hints[field.name], raw, fallback, path, issues)
    return cls(**values)


def _coerce_value(expected: Any, raw: Any, fallback: Any, path: str, issues: list[SettingsIssue]) -> Any:
    if is_dataclass_type(expected):
        return _coerce_dataclass(expected, raw, fallback, path, issues)
    origin = get_origin(expected)
    args = get_args(expected)
    if origin is list:
        if not isinstance(raw, list) or (args and any(not isinstance(item, str) for item in raw)):
            issues.append(SettingsIssue(path, "必须是字符串数组，已恢复默认值"))
            return list(fallback)
        return list(raw)
    if origin is dict:
        if not isinstance(raw, dict) or any(not isinstance(key, str) for key in raw):
            issues.append(SettingsIssue(path, "必须是对象，已恢复默认值"))
            return dict(fallback)
        if args and args[1] is str and any(not isinstance(item, str) for item in raw.values()):
            issues.append(SettingsIssue(path, "值必须是字符串，已恢复默认值"))
            return dict(fallback)
        return dict(raw)
    if expected is bool:
        valid = isinstance(raw, bool)
    elif expected is int:
        valid = isinstance(raw, int) and not isinstance(raw, bool)
    elif expected is float:
        valid = isinstance(raw, (int, float)) and not isinstance(raw, bool)
    elif expected is str:
        valid = isinstance(raw, str)
    else:
        valid = True
    if not valid:
        issues.append(SettingsIssue(path, "类型不正确，已恢复默认值"))
        return fallback
    return float(raw) if expected is float else raw


def is_dataclass_type(value: Any) -> bool:
    return isinstance(value, type) and is_dataclass(value)


def _join(prefix: str, key: str) -> str:
    return f"{prefix}.{key}" if prefix else key


__all__ = [
    "AiPrelabelSettings", "AnnotationSettings", "AppSettings", "ConversionSettings",
    "DatasetSettings", "FeatureSettings", "ImageResizeSettings", "LineToObbSettings",
    "ModelExportSettings", "PathSettings", "ProjectSettings", "RenameSettings",
    "SamAssistSettings", "SettingsIssue", "SettingsLoadResult", "SplitRatios",
    "TaskSettings", "TrainingSettings", "UiSettings", "ValidationSettings",
    "settings_from_dict", "settings_to_dict",
]
