from __future__ import annotations

import csv
import sys
from pathlib import Path

import yaml

from scr.paths import ROOT


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


def _read_yaml_mapping(path_like: str | Path | None) -> dict | None:
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
    payload = _read_yaml_mapping(path)
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


def app_cli_command(*args: str) -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, *args]
    return [sys.executable, "-m", "scr.main", *args]


def build_train_command(config: dict) -> list[str]:
    model = select_training_model(config)
    task_mode = infer_task_mode_from_config(config)
    command = app_cli_command("--yolo-train", task_mode, "train")
    fields = [
        ("model", model),
        ("data", config.get("data")),
        ("epochs", config.get("epochs")),
        ("imgsz", config.get("imgsz")),
        ("batch", config.get("batch")),
        ("workers", config.get("workers")),
        ("patience", config.get("patience")),
        ("project", config.get("project")),
        ("pretrained", config.get("pretrained")),
        ("device", config.get("device")),
        ("lr0", config.get("lr")),
        ("optimizer", config.get("optimizer")),
        ("mosaic", config.get("mosaic")),
        ("fliplr", config.get("fliplr")),
        ("flipud", config.get("flipud")),
        ("mixup", config.get("mixup")),
        ("scale", config.get("scale")),
        ("translate", config.get("translate")),
        ("degrees", config.get("degrees")),
        ("hsv_h", config.get("hsv_h", config.get("hsv"))),
        ("hsv_s", config.get("hsv_s")),
        ("hsv_v", config.get("hsv_v")),
    ]
    for key, value in fields:
        if value in (None, ""):
            continue
        command.append(f"{key}={value}")
    return command


def repair_validation_path_if_needed(dataset_yaml: str | Path | None) -> bool:
    path_text = str(dataset_yaml or "").strip()
    if not path_text:
        return False
    data_path = Path(path_text)
    payload = _read_yaml_mapping(data_path)
    if not isinstance(payload, dict):
        return False
    train_value = str(payload.get("train") or "").strip()
    val_value = str(payload.get("val") or "").strip()
    if not train_value or not val_value or "\\" not in val_value:
        return False

    train_path = Path(train_value.replace("\\", "/"))
    train_parts = list(train_path.parts)
    replaced = False
    for index, part in enumerate(train_parts):
        if part.lower() == "train":
            train_parts[index] = "val"
            replaced = True
            break
    if not replaced:
        return False

    repaired_val = str(Path(*train_parts)).replace("\\", "/")
    payload["val"] = repaired_val
    data_path.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return True


def build_export_command(model_path: str, export_format: str, imgsz: int | str = 640) -> list[str]:
    return app_cli_command("--yolo-export", f"model={model_path}", f"format={export_format}", f"imgsz={imgsz}")


def build_val_command(config: dict) -> list[str]:
    model = str(config.get("model_path") or "").strip()
    task_mode = infer_task_mode_from_model(model)
    command = app_cli_command("--yolo-val", task_mode, "val")
    fields = [
        ("model", model),
        ("data", config.get("data")),
        ("conf", config.get("confidence")),
        ("iou", config.get("iou")),
        ("imgsz", config.get("imgsz")),
        ("project", config.get("save_dir")),
    ]
    for key, value in fields:
        if value in (None, ""):
            continue
        command.append(f"{key}={value}")
    return command


def latest_result_csv(result_dir: Path) -> Path | None:
    candidates = sorted(Path(result_dir).glob("train*/results.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def _find_col(headers: list[str], prefixes: list[str]) -> str | None:
    for h in headers:
        for p in prefixes:
            if h.startswith(p):
                return h
    return None


def _parse_row(row: dict[str, str], headers: list[str]) -> dict[str, object]:
    metrics: dict[str, object] = {}
    try:
        metrics["epochs"] = int(float(row.get("epoch", 0)))
    except (ValueError, TypeError):
        pass
    try:
        raw_time = float(row.get("time", 0))
        total_sec = int(raw_time)
        hours, remainder = divmod(total_sec, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            metrics["train_time"] = f"{hours}h{minutes:02d}m{seconds:02d}s"
        else:
            metrics["train_time"] = f"{minutes}m{seconds:02d}s"
    except (ValueError, TypeError):
        pass
    map50_col = _find_col(headers, ["metrics/mAP50("])
    if map50_col:
        try:
            metrics["map50"] = f"{float(row[map50_col]) * 100:.1f}%"
        except (ValueError, TypeError):
            pass
    map5095_col = _find_col(headers, ["metrics/mAP50-95("])
    if map5095_col:
        try:
            metrics["map50_95"] = f"{float(row[map5095_col]) * 100:.1f}%"
        except (ValueError, TypeError):
            pass
    box_col = _find_col(headers, ["val/box_loss"])
    if box_col:
        try:
            metrics["box_loss"] = f"{float(row[box_col]):.4f}"
        except (ValueError, TypeError):
            pass
    recall_col = _find_col(headers, ["metrics/recall("])
    if recall_col:
        try:
            metrics["recall"] = f"{float(row[recall_col]) * 100:.1f}%"
        except (ValueError, TypeError):
            pass
    return metrics


def _select_best_metrics_row(
    rows: list[dict[str, str]], headers: list[str]
) -> dict[str, str]:
    fitness_col = _find_col(headers, ["fitness"])
    if fitness_col:
        best_row = rows[-1]
        best_val = float("-inf")
        for row in rows:
            try:
                val = float(row.get(fitness_col, float("-inf")))
            except (ValueError, TypeError):
                continue
            if val >= best_val:
                best_val = val
                best_row = row
        return best_row

    # Ultralytics 8.4.x detect/obb best.pt follows validation fitness, which is
    # currently aligned with mAP50-95 rather than raw mAP50.
    for prefixes in (["metrics/mAP50-95("], ["metrics/mAP50("]):
        metric_col = _find_col(headers, prefixes)
        if not metric_col:
            continue
        best_row = rows[-1]
        best_val = float("-inf")
        for row in rows:
            try:
                val = float(row.get(metric_col, float("-inf")))
            except (ValueError, TypeError):
                continue
            if val >= best_val:
                best_val = val
                best_row = row
        return best_row

    return rows[-1]


def read_train_metrics(run_dir: Path, model_filename: str = "") -> dict[str, object]:
    csv_path = run_dir / "results.csv"
    if not csv_path.exists():
        return {}
    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        if not rows:
            return {}
        headers = list(rows[0].keys())
        is_best = model_filename.lower() == "best.pt"
        if is_best:
            return _parse_row(_select_best_metrics_row(rows, headers), headers)
        else:
            return _parse_row(rows[-1], headers)
    except Exception:
        return {}


def read_results_csv_for_curves(result_dir: Path) -> dict[str, list[float]]:
    """Read the latest results.csv and return column data for plotting curves."""
    csv_path = latest_result_csv(result_dir)
    if csv_path is None or not csv_path.exists():
        return {}
    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        if not rows:
            return {}
        headers = list(rows[0].keys())
        data: dict[str, list[float]] = {}
        for h in headers:
            vals = []
            for row in rows:
                try:
                    vals.append(float(row[h]))
                except (ValueError, TypeError):
                    vals.append(0.0)
            data[h] = vals
        return data
    except Exception:
        return {}
