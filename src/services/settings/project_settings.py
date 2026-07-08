from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.services.settings.defaults import build_default_settings
from src.services.settings.storage import (
    PROJECT_PATH_FIELDS,
    deep_merge,
    deserialize_settings_from_storage,
    serialize_settings_for_storage,
)
from src.shared.paths import ROOT, RUNTIME_ROOT


APP_STATE_PATH = RUNTIME_ROOT / "app_state.json"


def project_settings_path(project_root: Path = ROOT) -> Path:
    return Path(project_root) / "data" / "runtime" / "settings.json"


def load_last_project_root(app_state_path: Path | None = None, fallback: Path = ROOT) -> Path:
    fallback = Path(fallback)
    app_state_path = Path(app_state_path or APP_STATE_PATH)
    try:
        payload = json.loads(app_state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return fallback
    raw_path = payload.get("last_project_root")
    if not raw_path:
        return fallback
    candidate = Path(raw_path).expanduser()
    if not candidate.exists():
        return fallback
    return candidate.resolve()


def save_last_project_root(
    project_root: Path, app_state_path: Path | None = None
) -> None:
    app_state_path = Path(app_state_path or APP_STATE_PATH)
    app_state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"last_project_root": str(Path(project_root).resolve())}
    app_state_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


class SettingsService:
    def __init__(self, settings_path: Path | None = None, project_root: Path | None = None):
        resolved_root = (
            load_last_project_root() if project_root is None else Path(project_root)
        )
        self.project_root = resolved_root
        self.settings_path = Path(settings_path) if settings_path is not None else project_settings_path(self.project_root)

    def load(self) -> dict[str, Any]:
        defaults = build_default_settings(self.project_root)
        if not self.settings_path.exists():
            self.save(defaults)
            return defaults
        try:
            payload = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            payload = {}
        settings = deserialize_settings_from_storage(
            deep_merge(defaults, payload), self.project_root
        )
        settings.setdefault("project", {})["root"] = str(self.project_root)
        self.save(settings)
        return settings

    def reset_to_defaults(self) -> dict[str, Any]:
        defaults = build_default_settings(self.project_root)
        self.save(defaults)
        return defaults

    def save(self, data: dict[str, Any]) -> None:
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        serialized = serialize_settings_for_storage(data, self.project_root)
        self.settings_path.write_text(
            json.dumps(serialized, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        save_last_project_root(self.project_root)


