from __future__ import annotations

from pathlib import Path

import yaml

from src.shared.paths import ROOT


def infer_task_mode_from_model(model_name: str | Path | None) -> str:
    name = Path(str(model_name or "")).name.lower()
    return "obb" if "obb" in name else "detect"


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
    return [path.name for path in find_training_model_paths(project_root, app_root)]


def find_model_yaml_files(data_dir: Path) -> list[str]:
    if not data_dir.exists():
        return []
    return [str(path) for path in sorted(data_dir.glob("*.yaml")) if path.is_file()]


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


def read_yaml_mapping(path_like: str | Path | None) -> dict | None:
    path_text = str(path_like or "").strip()
    if not path_text:
        return None
    path = Path(path_text)
    if path.suffix.lower() not in {".yaml", ".yml"} or not path.exists():
        return None
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def is_dataset_yaml(path_like: str | Path | None) -> bool:
    path_text = str(path_like or "").strip()
    if not path_text:
        return False
    path = Path(path_text)
    if path.suffix.lower() not in {".yaml", ".yml"}:
        return False
    if path.name.lower() == "data.yaml":
        return True
    payload = read_yaml_mapping(path)
    if payload is None:
        return False
    keys = set(payload)
    has_model_keys = {"backbone", "head"} & keys
    has_dataset_keys = {"path", "train", "val", "test", "names", "nc"} & keys
    return bool(has_dataset_keys) and not has_model_keys


def select_training_model(config: dict) -> str:
    model_yaml = config.get("model_yaml")
    if model_yaml and not is_dataset_yaml(model_yaml):
        return str(model_yaml)
    for key in ("base_model", "model", "pretrained"):
        value = config.get(key)
        if key == "model" and is_dataset_yaml(value):
            continue
        if value:
            return str(value)
    return ""


def infer_task_mode_from_config(config: dict) -> str:
    for key in ("model_yaml", "base_model", "model", "pretrained"):
        if infer_task_mode_from_model(config.get(key)) == "obb":
            return "obb"
    return "detect"
