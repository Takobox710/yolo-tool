from __future__ import annotations

import re
from pathlib import Path


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp"}
VIDEO_SUFFIXES = {".mp4", ".avi", ".mov", ".mkv"}
SOURCE_SUFFIXES = IMAGE_SUFFIXES | VIDEO_SUFFIXES


def natural_sort_key(path: Path) -> list[object]:
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", path.name)
    ]


def scan_candidate_models(result_dir: Path) -> list[Path]:
    root = Path(result_dir)
    if not root.exists():
        return []
    run_dirs = sorted(
        [path for path in root.glob("train*") if path.is_dir()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    candidates: list[Path] = []
    for run_dir in run_dirs:
        for name in ("best.pt", "last.pt"):
            model = run_dir / "weights" / name
            if model.exists():
                candidates.append(model)
    return candidates


def find_result_model_paths(
    result_dir: Path, *, show_last_training_models: bool = True
) -> list[Path]:
    models = scan_candidate_models(result_dir)
    if show_last_training_models:
        return models
    return [path for path in models if path.name.lower() != "last.pt"]


def is_live_source_mode(source_mode: str) -> bool:
    return str(source_mode).strip() == "摄像头"


def should_store_detection_history(source_mode: str) -> bool:
    return not is_live_source_mode(source_mode)


def detection_counter_text(
    source_mode: str, detect_index: int, result_count: int
) -> str:
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
    fps_text = (
        f"实时帧率 FPS: {fps:.1f}"
        if payload.get("stream_mode")
        else f"FPS: {fps:.1f}"
    )
    return (
        f"{payload.get('status')} | 单张耗时: {elapsed * 1000:.1f}ms | "
        f"{fps_text} | 结果: {len(payload.get('items') or [])} 个"
    )
