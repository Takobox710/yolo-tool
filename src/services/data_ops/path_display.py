from __future__ import annotations

import os
from pathlib import Path

from src.shared.paths import ROOT


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


def relative_path_from_project(path_str: str, project_root: str | Path = ROOT) -> str:
    if not path_str:
        return ""
    root = Path(project_root).expanduser().resolve()
    resolved = Path(resolve_project_path(path_str, root))
    try:
        return os.path.relpath(str(resolved), str(root))
    except ValueError:
        return str(resolved)


def relative_project_path(path_str: str, project_root: str | Path = ROOT) -> str:
    return display_project_path(path_str, project_root)


def simplified_model_path(path_str: str, project_root: str | Path = ROOT) -> str:
    rel = relative_project_path(path_str, project_root)
    parts = Path(rel).parts
    if len(parts) >= 3 and parts[0].lower() == "result" and parts[-2].lower() == "weights":
        return str(Path(*parts[1:-2] + (parts[-1],)))
    return rel


