from __future__ import annotations

import csv
from pathlib import Path


def infer_task_mode_from_model(model_name: str | Path | None) -> str:
    name = Path(str(model_name or "")).name.lower()
    return "obb" if "obb" in name else "detect"


def build_train_command(config: dict) -> list[str]:
    model = config.get("model_yaml") or config.get("base_model") or config.get("model")
    task_mode = infer_task_mode_from_model(model)
    command = ["pixi", "run", "yolo", task_mode, "train"]
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
        ("mosaic", config.get("mosaic")),
        ("fliplr", config.get("fliplr")),
        ("flipud", config.get("flipud")),
        ("mixup", config.get("mixup")),
        ("scale", config.get("scale")),
        ("translate", config.get("translate")),
        ("degrees", config.get("degrees")),
    ]
    for key, value in fields:
        if value in (None, ""):
            continue
        command.append(f"{key}={value}")
    return command


def build_export_command(model_path: str, export_format: str, imgsz: int | str = 640) -> list[str]:
    return ["pixi", "run", "yolo", "export", f"model={model_path}", f"format={export_format}", f"imgsz={imgsz}"]


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
    """从 results.csv 的一行数据中提取关键指标。"""
    metrics: dict[str, object] = {}

    # epoch
    try:
        metrics["epochs"] = int(float(row.get("epoch", 0)))
    except (ValueError, TypeError):
        pass

    # time → 格式化
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

    # mAP50 — 兼容 (B) 和 (OBB)
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

    # val/box_loss
    box_col = _find_col(headers, ["val/box_loss"])
    if box_col:
        try:
            metrics["box_loss"] = f"{float(row[box_col]):.4f}"
        except (ValueError, TypeError):
            pass

    # metrics/recall(B) 或 (OBB)
    recall_col = _find_col(headers, ["metrics/recall("])
    if recall_col:
        try:
            metrics["recall"] = f"{float(row[recall_col]) * 100:.1f}%"
        except (ValueError, TypeError):
            pass

    return metrics


def read_train_metrics(run_dir: Path, model_filename: str = "") -> dict[str, object]:
    """读取训练 run 目录中的 results.csv，提取关键指标。

    Parameters
    ----------
    run_dir : Path
        训练 run 目录，例如 result/train/ 或 result/train-2/
    model_filename : str
        模型文件名，如 "best.pt" 或 "last.pt"。
        best.pt 读取 mAP50 最高的那一行，last.pt 读取最后一行。

    Returns
    -------
    dict with keys: epochs, train_time, map50, map50_95, box_loss, recall
    """
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
            # 找 mAP50 最大的那一行
            map50_col = _find_col(headers, ["metrics/mAP50("])
            best_row = rows[-1]
            best_val = -1.0
            for row in rows:
                try:
                    val = float(row.get(map50_col, -1)) if map50_col else -1.0
                    if val > best_val:
                        best_val = val
                        best_row = row
                except (ValueError, TypeError):
                    continue
            return _parse_row(best_row, headers)
        else:
            return _parse_row(rows[-1], headers)
    except Exception:
        return {}
