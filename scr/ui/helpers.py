from __future__ import annotations

import re
from pathlib import Path

from scr.paths import ROOT
from scr.services.path_service import (
    display_project_path,
    relative_project_path,
    resolve_project_path,
    simplified_model_path,
)


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


_resolve_project_path = resolve_project_path
_display_project_path = display_project_path
_relative_path = relative_project_path
_simplified_model_path = simplified_model_path
_home_column_widths = home_column_widths
_history_model_sort_key = history_model_sort_key
_history_number_sort_key = history_number_sort_key
_history_time_sort_key = history_time_sort_key
_parse_padding_text = parse_padding_text
