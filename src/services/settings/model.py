from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from typing import Any, get_args, get_origin, get_type_hints


@dataclass(slots=True)
class SettingsIssue:
    path: str
    message: str


@dataclass(slots=True)
class SettingsLoadResult:
    settings: AppSettings
    migrated: bool = False
    issues: tuple[SettingsIssue, ...] = ()


@dataclass(slots=True)
class ProjectSettings:
    root: str


@dataclass(slots=True)
class PathSettings:
    images_dir: str
    annotations_dir: str
    labels_dir: str
    dataset_dir: str
    models_dir: str
    result_dir: str


@dataclass(slots=True)
class TaskSettings:
    mode: str


@dataclass(slots=True)
class SplitRatios:
    train: float
    val: float
    test: float


@dataclass(slots=True)
class LineToObbSettings:
    enabled: bool
    half_width: float


@dataclass(slots=True)
class DatasetSettings:
    class_names: list[str]
    split_ratios: SplitRatios
    line_to_obb: LineToObbSettings
    random_seed: int


@dataclass(slots=True)
class ImageResizeSettings:
    source_dir: str
    long_edge: int
    canvas_size: int
    background: str
    output_dir: str
    backup_dir: str
    backup_enabled: bool


@dataclass(slots=True)
class TrainingSettings:
    model_yaml: str
    base_model: str
    pretrained: str
    data: str
    project: str
    export_format: str
    lr: float
    epochs: int
    patience: int
    workers: int
    batch: int
    imgsz: int
    device: str
    mosaic: float
    fliplr: float
    flipud: float
    mixup: float
    scale: float
    translate: float
    degrees: float
    hsv_h: float
    hsv_s: float
    hsv_v: float
    optimizer: str


@dataclass(slots=True)
class ValidationSettings:
    model_path: str
    source_mode: str
    source_path: str
    source_selection: str
    data: str
    source_scope: str
    camera_index: int
    confidence: float
    iou: float
    imgsz: int
    save_dir: str


@dataclass(slots=True)
class ConversionSettings:
    use_labelme: bool
    backup_yolo_files: bool
    class_name_mappings: dict[str, str]


@dataclass(slots=True)
class ModelExportSettings:
    model_path: str
    output_dir: str
    format: str
    imgsz: int
    simplify: bool


@dataclass(slots=True)
class AiPrelabelSettings:
    model_path: str
    confidence: float
    iou: float
    range_mode: str
    process_mode: str
    custom_selected_images: list[str]


@dataclass(slots=True)
class AnnotationSettings:
    auto_save: bool
    auto_convert_yolo: bool
    show_yolo_save_in_context_menu: bool
    show_annotation_names: bool
    show_canvas_status: bool
    continuous_draw: bool
    quick_draw: bool
    line_expand_enabled: bool
    line_expand_pixels: int
    optimize_mirror_edit: bool
    ai_prelabel: AiPrelabelSettings


@dataclass(slots=True)
class RenameSettings:
    prefix: str
    start_index: int
    padding: int
    include_labelme: bool
    include_yolo: bool


@dataclass(slots=True)
class UiSettings:
    last_page: str
    window_width: int
    window_height: int


@dataclass(slots=True)
class FeatureSettings:
    distribution_multi_class_mode: bool
    custom_command_dialog: bool
    show_help_icons: bool
    show_last_training_models: bool
    resize_output_mode: str


@dataclass(slots=True)
class AppSettings:
    project: ProjectSettings
    paths: PathSettings
    task: TaskSettings
    dataset: DatasetSettings
    image_resize: ImageResizeSettings
    training: TrainingSettings
    validation: ValidationSettings
    conversion: ConversionSettings
    model_export: ModelExportSettings
    annotation: AnnotationSettings
    rename: RenameSettings
    ui: UiSettings
    features: FeatureSettings
    schema_version: int = 1


def settings_to_dict(settings: AppSettings) -> dict[str, Any]:
    return _dataclass_to_dict(settings)


def settings_from_dict(
    payload: dict[str, Any], defaults: AppSettings
) -> tuple[AppSettings, tuple[SettingsIssue, ...]]:
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


def _coerce_dataclass(
    cls: type,
    payload: Any,
    defaults: Any,
    prefix: str,
    issues: list[SettingsIssue],
) -> Any:
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


def _coerce_value(
    expected: Any,
    raw: Any,
    fallback: Any,
    path: str,
    issues: list[SettingsIssue],
) -> Any:
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
        issues.append(SettingsIssue(path, f"类型不正确，已恢复默认值"))
        return fallback
    return float(raw) if expected is float else raw


def is_dataclass_type(value: Any) -> bool:
    return isinstance(value, type) and is_dataclass(value)


def _join(prefix: str, key: str) -> str:
    return f"{prefix}.{key}" if prefix else key


__all__ = [
    "AiPrelabelSettings",
    "AnnotationSettings",
    "AppSettings",
    "ConversionSettings",
    "DatasetSettings",
    "FeatureSettings",
    "ImageResizeSettings",
    "LineToObbSettings",
    "ModelExportSettings",
    "PathSettings",
    "ProjectSettings",
    "RenameSettings",
    "SettingsIssue",
    "SettingsLoadResult",
    "SplitRatios",
    "TaskSettings",
    "TrainingSettings",
    "UiSettings",
    "ValidationSettings",
    "settings_from_dict",
    "settings_to_dict",
]
