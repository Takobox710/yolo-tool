from __future__ import annotations

from dataclasses import dataclass


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
    mode_selected: bool


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
    precision: str
    batch: int
    dynamic_batch: bool
    dynamic_height: bool
    dynamic_width: bool
    nms: bool
    nms_conf: float
    nms_iou: float
    nms_max_det: int
    agnostic_nms: bool
    opset: int | None
    workspace: float | None
    optimize: bool
    calibration_data: str
    calibration_samples: int
    validate_quantized: bool
    validation_samples: int


@dataclass(slots=True)
class AiPrelabelSettings:
    model_path: str
    confidence: float
    iou: float
    sam3_confidence: float
    sam3_dedup_iou: float
    sam3_output_shape: str
    sam3_prompts: dict[str, str]
    sam3_enabled_classes: list[str]
    sam3_min_area: int
    sam3_polygon_simplify_ratio: float
    range_mode: str
    process_mode: str
    custom_selected_images: list[str]


@dataclass(slots=True)
class SamAssistSettings:
    model_path: str
    multimask_output: bool
    minimum_score: float
    minimum_area: int
    polygon_simplification_ratio: float


@dataclass(slots=True)
class AnnotationSettings:
    auto_save: bool
    auto_convert_yolo: bool
    show_yolo_save_in_context_menu: bool
    load_yolo_when_labelme_missing: bool
    show_annotation_names: bool
    show_canvas_status: bool
    continuous_draw: bool
    quick_draw: bool
    line_expand_enabled: bool
    line_expand_pixels: int
    optimize_mirror_edit: bool
    ai_prelabel: AiPrelabelSettings
    sam_assist: SamAssistSettings


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


__all__ = [name for name in globals() if name.endswith("Settings") or name in {"AppSettings", "SettingsIssue", "SettingsLoadResult", "SplitRatios", "LineToObbSettings"}]
