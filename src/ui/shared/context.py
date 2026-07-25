from __future__ import annotations

from collections.abc import Callable
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any

from src.services.settings import (
    AppSettings,
    SettingsLoadResult,
    SettingsService,
    settings_to_dict,
)
from src.ui.shared.tasks import TaskCoordinator


class WorkbenchContext:
    """Explicit page-facing application services and current project state."""

    def __init__(
        self,
        settings_service: SettingsService,
        load_result: SettingsLoadResult,
        *,
        append_log: Callable[..., None] | None = None,
        program_log: Callable[[], str] | None = None,
        notify_settings: Callable[..., None] | None = None,
        run_background: Callable[..., Any] | None = None,
        switch_project: Callable[[str | Path], None] | None = None,
        reset_settings: Callable[..., AppSettings] | None = None,
        refresh_help_icons: Callable[[], None] | None = None,
        refresh_validation_models: Callable[[], None] | None = None,
    ) -> None:
        self.settings_service = settings_service
        self.settings = load_result.settings
        self.load_result = load_result
        self.tasks = TaskCoordinator()
        self.generation = 0
        self._append_log = append_log
        self._program_log = program_log
        self._notify_settings = notify_settings
        self._run_background = run_background
        self._switch_project = switch_project
        self._reset_settings = reset_settings
        self._refresh_help_icons = refresh_help_icons
        self._refresh_validation_models = refresh_validation_models
        self._saved_snapshot = _snapshot(self.settings)

    @property
    def project_root(self) -> Path:
        return Path(self.settings.project.root)

    def save_settings(self, *, source: object | None = None) -> tuple[str, ...]:
        changed = _changed_paths(self._saved_snapshot, self.settings)
        self.settings_service.save(self.settings)
        self._saved_snapshot = _snapshot(self.settings)
        if changed and self._notify_settings is not None:
            self._notify_settings(changed, source=source)
        return changed

    def replace_settings(
        self,
        settings_service: SettingsService,
        load_result: SettingsLoadResult,
    ) -> None:
        self.settings_service = settings_service
        self.settings = load_result.settings
        self.load_result = load_result
        self.generation += 1
        self._saved_snapshot = _snapshot(self.settings)

    def append_program_log(self, text: str, *, level: str | None = None) -> None:
        if self._append_log is not None:
            self._append_log(text, level=level)

    def program_log_text(self) -> str:
        if self._program_log is None:
            return "等待程序日志..."
        return str(self._program_log())

    def run_background(self, kind: str, fn: Callable[[], Any], receiver=None):
        if self._run_background is None:
            return None
        return self._run_background(kind, fn, receiver=receiver)

    def switch_project_root(self, project_root: str | Path) -> None:
        if self._switch_project is not None:
            self._switch_project(project_root)

    def reset_project_settings(self, current_page: str | None = None):
        if self._reset_settings is None:
            return self.settings
        return self._reset_settings(current_page)

    def refresh_help_icons(self) -> None:
        if self._refresh_help_icons is not None:
            self._refresh_help_icons()

    def refresh_validation_models(self) -> None:
        if self._refresh_validation_models is not None:
            self._refresh_validation_models()


def _snapshot(value: Any) -> Any:
    if is_dataclass(value):
        return {field.name: _snapshot(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, list):
        return [_snapshot(item) for item in value]
    if isinstance(value, dict):
        return {key: _snapshot(item) for key, item in value.items()}
    return value


def _changed_paths(before: Any, after: Any, prefix: str = "") -> tuple[str, ...]:
    if isinstance(before, dict) and isinstance(after, dict):
        keys = set(before) | set(after)
        changed: list[str] = []
        for key in sorted(keys):
            changed.extend(_changed_paths(before.get(key), after.get(key), _join(prefix, key)))
        return tuple(changed)
    if before != after:
        return (prefix,)
    return ()


def _join(prefix: str, key: str) -> str:
    return f"{prefix}.{key}" if prefix else key


__all__ = ["WorkbenchContext"]
