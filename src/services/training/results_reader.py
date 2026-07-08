from __future__ import annotations

import csv
from pathlib import Path


def latest_result_csv(result_dir: Path) -> Path | None:
    candidates = sorted(
        Path(result_dir).glob("train*/results.csv"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _find_col(headers: list[str], prefixes: list[str]) -> str | None:
    for header in headers:
        for prefix in prefixes:
            if header.startswith(prefix):
                return header
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
        metrics["train_time"] = (
            f"{hours}h{minutes:02d}m{seconds:02d}s"
            if hours > 0
            else f"{minutes}m{seconds:02d}s"
        )
    except (ValueError, TypeError):
        pass
    _append_percent_metric(metrics, row, headers, "map50", ["metrics/mAP50("])
    _append_percent_metric(metrics, row, headers, "map50_95", ["metrics/mAP50-95("])
    _append_decimal_metric(metrics, row, headers, "box_loss", ["val/box_loss"], "{:.4f}")
    _append_percent_metric(metrics, row, headers, "recall", ["metrics/recall("])
    return metrics


def _append_percent_metric(
    metrics: dict[str, object],
    row: dict[str, str],
    headers: list[str],
    target_key: str,
    prefixes: list[str],
) -> None:
    column = _find_col(headers, prefixes)
    if not column:
        return
    try:
        metrics[target_key] = f"{float(row[column]) * 100:.1f}%"
    except (ValueError, TypeError):
        return


def _append_decimal_metric(
    metrics: dict[str, object],
    row: dict[str, str],
    headers: list[str],
    target_key: str,
    prefixes: list[str],
    template: str,
) -> None:
    column = _find_col(headers, prefixes)
    if not column:
        return
    try:
        metrics[target_key] = template.format(float(row[column]))
    except (ValueError, TypeError):
        return


def _select_best_metrics_row(
    rows: list[dict[str, str]], headers: list[str]
) -> dict[str, str]:
    fitness_col = _find_col(headers, ["fitness"])
    if fitness_col:
        return _row_with_max_metric(rows, fitness_col)
    for prefixes in (["metrics/mAP50-95("], ["metrics/mAP50("]):
        metric_col = _find_col(headers, prefixes)
        if metric_col:
            return _row_with_max_metric(rows, metric_col)
    return rows[-1]


def _row_with_max_metric(rows: list[dict[str, str]], column: str) -> dict[str, str]:
    best_row = rows[-1]
    best_val = float("-inf")
    for row in rows:
        try:
            value = float(row.get(column, float("-inf")))
        except (ValueError, TypeError):
            continue
        if value >= best_val:
            best_val = value
            best_row = row
    return best_row


def read_train_metrics(run_dir: Path, model_filename: str = "") -> dict[str, object]:
    csv_path = run_dir / "results.csv"
    if not csv_path.exists():
        return {}
    try:
        with open(csv_path, newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
        if not rows:
            return {}
        headers = list(rows[0].keys())
        row = (
            _select_best_metrics_row(rows, headers)
            if model_filename.lower() == "best.pt"
            else rows[-1]
        )
        return _parse_row(row, headers)
    except Exception:
        return {}


def read_results_csv_for_curves(result_dir: Path) -> dict[str, list[float]]:
    csv_path = latest_result_csv(result_dir)
    if csv_path is None or not csv_path.exists():
        return {}
    try:
        with open(csv_path, newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
        if not rows:
            return {}
        headers = list(rows[0].keys())
        data: dict[str, list[float]] = {}
        for header in headers:
            data[header] = [_float_or_zero(row.get(header)) for row in rows]
        return data
    except Exception:
        return {}


def _float_or_zero(value: str | None) -> float:
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0
