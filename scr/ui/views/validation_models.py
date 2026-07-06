from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from scr.services.detection_service import find_result_model_paths
from scr.services.path_service import simplified_model_path
from scr.services.training_service import find_training_model_paths


@dataclass
class ValidationModelChoices:
    all_paths: list[Path]
    display_paths: dict[str, Path]
    display_names: list[str]
    selected_display: str


def build_validation_model_choices(
    *,
    current_text: str | None,
    current_display_paths: dict[str, Path],
    project_root: Path,
    result_dir: Path,
    show_last_training_models: bool,
    resolve_text: Callable[[str], str],
) -> ValidationModelChoices:
    selected_text = str(current_text or "").strip()
    mapped_current = current_display_paths.get(selected_text)
    current_path = mapped_current
    if current_path is None and selected_text:
        current_path = Path(selected_text)
        if not current_path.is_absolute():
            current_path = Path(resolve_text(selected_text))

    all_paths: list[Path] = []
    display_paths: dict[str, Path] = {}
    seen: set[str] = set()
    for path in find_training_model_paths(project_root, project_root):
        resolved_path = path.resolve()
        resolved = str(resolved_path)
        if resolved in seen:
            continue
        all_paths.append(resolved_path)
        display_paths[simplified_model_path(str(resolved_path), project_root)] = resolved_path
        seen.add(resolved)

    for path in find_result_model_paths(
        result_dir, show_last_training_models=show_last_training_models
    ):
        resolved_path = path.resolve()
        resolved = str(resolved_path)
        if resolved in seen:
            continue
        all_paths.append(resolved_path)
        display_paths[simplified_model_path(str(resolved_path), project_root)] = resolved_path
        seen.add(resolved)

    display_names = list(display_paths.keys())
    selected_display = selected_text
    if current_path:
        for display_name, resolved_path in display_paths.items():
            if resolved_path == current_path:
                selected_display = display_name
                break
        else:
            if (
                not show_last_training_models
                and current_path.name.lower() == "last.pt"
                and current_path.parent.name.lower() == "weights"
            ):
                best_path = current_path.with_name("best.pt")
                best_display = simplified_model_path(str(best_path), project_root)
                if best_display in display_paths:
                    selected_display = best_display
            elif current_path.exists():
                selected_display = simplified_model_path(str(current_path), project_root)
    if not selected_display and display_names:
        selected_display = display_names[0]

    return ValidationModelChoices(
        all_paths=all_paths,
        display_paths=display_paths,
        display_names=display_names,
        selected_display=selected_display,
    )
