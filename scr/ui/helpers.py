from __future__ import annotations

import os
import re
from pathlib import Path

from scr.paths import ROOT
from scr.services.detection_service import scan_candidate_models


def resolve_project_path(path_str: str, project_root: str | Path = ROOT) -> str:
    text = str(path_str or "").strip().strip('"')
    if not text:
        return ""
    root = Path(project_root).expanduser().resolve()
    path = Path(os.path.expandvars(text)).expanduser()
    if path.is_absolute():
        return str(path.resolve())
    return str((root / path).resolve())


def display_project_path(path_str: str, project_root: str | Path = ROOT) -> str:
    if not path_str:
        return ""
    root = Path(project_root).expanduser().resolve()
    resolved = Path(resolve_project_path(path_str, root))
    try:
        common = os.path.commonpath([str(root), str(resolved)])
    except ValueError:
        return str(resolved)
    if os.path.normcase(common) == os.path.normcase(str(root)):
        return os.path.relpath(str(resolved), str(root))
    return str(resolved)


def relative_path(path_str: str, project_root: str | Path = ROOT) -> str:
    return display_project_path(path_str, project_root)


def simplified_model_path(path_str: str, project_root: str | Path = ROOT) -> str:
    rel = relative_path(path_str, project_root)
    parts = Path(rel).parts
    if len(parts) >= 3 and parts[0].lower() == "result" and parts[-2].lower() == "weights":
        return str(Path(*parts[1:-2] + (parts[-1],)))
    return rel


def find_models_in_dir(result_dir: Path, project_root: str | Path = ROOT) -> list[str]:
    return [
        simplified_model_path(str(model), project_root)
        for model in scan_candidate_models(result_dir)
    ]


def find_models_full_paths(
    result_dir: Path, *, show_last_training_models: bool = True
) -> list[Path]:
    models = scan_candidate_models(result_dir)
    if show_last_training_models:
        return models
    return [path for path in models if path.name.lower() != "last.pt"]


def find_model_yaml_files(data_dir: Path) -> list[str]:
    if not data_dir.exists():
        return []
    return [str(path) for path in sorted(data_dir.glob("*.yaml")) if path.is_file()]


def find_pt_files_in_data_models(project_root: Path) -> list[str]:
    return find_training_model_names(project_root)


def training_model_dirs(project_root: Path, app_root: Path | None = None) -> list[Path]:
    app_root = ROOT if app_root is None else Path(app_root)
    project_models_dir = (Path(project_root) / "data" / "models").resolve()
    app_models_dir = (app_root / "data" / "models").resolve()
    model_dirs = [project_models_dir]
    if app_models_dir != project_models_dir:
        model_dirs.append(app_models_dir)
    return model_dirs


def find_training_model_paths(project_root: Path, app_root: Path | None = None) -> list[Path]:
    paths: list[Path] = []
    names: set[str] = set()
    for models_dir in training_model_dirs(project_root, app_root):
        if not models_dir.exists():
            continue
        for path in sorted(models_dir.glob("*.pt")):
            if path.is_file() and path.name not in names:
                paths.append(path.resolve())
                names.add(path.name)
    return paths


def find_training_model_names(project_root: Path, app_root: Path | None = None) -> list[str]:
    names: list[str] = []
    for path in find_training_model_paths(project_root, app_root):
        names.append(path.name)
    return names


def resolve_training_model_reference(
    model_text: str,
    project_root: Path,
    app_root: Path | None = None,
) -> str:
    text = str(model_text or "").strip()
    if not text:
        return ""

    path = Path(text)
    if path.is_absolute():
        return str(path.resolve()) if path.exists() else str(path)

    resolved_project_root = Path(project_root).resolve()
    resolved_app_root = Path(ROOT if app_root is None else app_root).resolve()
    project_models_dir = resolved_project_root / "data" / "models"
    app_models_dir = resolved_app_root / "data" / "models"

    candidates: list[Path] = []
    if len(path.parts) == 1:
        candidates.append(project_models_dir / text)
        if app_models_dir != project_models_dir:
            candidates.append(app_models_dir / text)
    candidates.append(resolved_project_root / text)
    if resolved_app_root != resolved_project_root:
        candidates.append(resolved_app_root / text)

    for candidate in candidates:
        if candidate.exists():
            return str(candidate.resolve())

    if path.suffix.lower() == ".pt" and len(path.parts) == 1:
        return str((project_models_dir / text).resolve())
    return text


def home_column_widths(total_width: int, margins: int = 32, spacing: int = 12) -> tuple[int, int]:
    content_width = max(int(total_width) - margins - spacing, 3)
    left = content_width * 3 // 10
    right = content_width - left
    return left, right


def history_model_sort_key(train_id: str, model_name: str) -> float:
    match = re.fullmatch(r"train(?:-(\d+))?", str(train_id).strip())
    run_number = int(match.group(1) or 1) if match else 0
    model_priority = 1 if str(model_name).lower() == "best.pt" else 0
    return float(-(run_number * 10 + model_priority))


def history_number_sort_key(value: object) -> float:
    try:
        return float(str(value).strip().replace("%", ""))
    except (ValueError, TypeError):
        return 0.0


def history_time_sort_key(value: object) -> float:
    text = str(value).strip()
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        pass
    match = re.fullmatch(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", text)
    if not match:
        return 0.0
    hours, minutes, seconds = (int(part or 0) for part in match.groups())
    return float(hours * 3600 + minutes * 60 + seconds)


def parse_padding_text(text: str) -> int:
    value = str(text or "").strip()
    return int(value) if value else 0


def is_live_source_mode(source_mode: str) -> bool:
    return str(source_mode).strip() == "摄像头"


def should_store_detection_history(source_mode: str) -> bool:
    return not is_live_source_mode(source_mode)


def detection_counter_text(source_mode: str, detect_index: int, result_count: int) -> str:
    if is_live_source_mode(source_mode):
        return "实时预览"
    if result_count <= 0 or detect_index < 0:
        return "0/0"
    return f"{detect_index + 1}/{result_count}"


def build_detection_log_message(payload: dict) -> str:
    elapsed = float(payload.get("elapsed") or 0.0)
    fps = payload.get("fps")
    if fps is None:
        fps = (1 / elapsed) if elapsed else 0.0
    fps_text = f"实时帧率 FPS: {fps:.1f}" if payload.get("stream_mode") else f"FPS: {fps:.1f}"
    return f"{payload.get('status')} | 单张耗时: {elapsed * 1000:.1f}ms | {fps_text} | 结果: {len(payload.get('items') or [])} 个"


_resolve_project_path = resolve_project_path
_display_project_path = display_project_path
_relative_path = relative_path
_simplified_model_path = simplified_model_path
_find_models_in_dir = find_models_in_dir
_find_models_full_paths = find_models_full_paths
_find_model_yaml_files = find_model_yaml_files
_find_pt_files_in_data_models = find_pt_files_in_data_models
_find_training_model_paths = find_training_model_paths
_find_training_model_names = find_training_model_names
_resolve_training_model_reference = resolve_training_model_reference
_home_column_widths = home_column_widths
_history_model_sort_key = history_model_sort_key
_history_number_sort_key = history_number_sort_key
_history_time_sort_key = history_time_sort_key
_parse_padding_text = parse_padding_text
_is_live_source_mode = is_live_source_mode
_should_store_detection_history = should_store_detection_history
_detection_counter_text = detection_counter_text
_build_detection_log_message = build_detection_log_message
