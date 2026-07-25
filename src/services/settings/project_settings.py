from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.services.settings.defaults import build_default_settings
from src.services.settings.model import (
    AppSettings,
    SettingsIssue,
    SettingsLoadResult,
    settings_from_dict,
    settings_to_dict,
)
from src.services.settings.storage import (
    PROJECT_PATH_FIELDS,
    deep_merge,
    deserialize_settings_from_storage,
    serialize_settings_for_storage,
)
from src.shared.paths import ROOT, RUNTIME_ROOT


APP_STATE_PATH = RUNTIME_ROOT / "app_state.json"


@dataclass(slots=True)
class AppState:
    last_project_root: str = str(ROOT)


def project_settings_path(project_root: Path = ROOT) -> Path:
    return Path(project_root) / "data" / "runtime" / "settings.json"


def load_last_project_root(app_state_path: Path | None = None, fallback: Path = ROOT) -> Path:
    fallback = Path(fallback)
    app_state_path = Path(app_state_path or APP_STATE_PATH)
    try:
        payload = json.loads(app_state_path.read_text(encoding="utf-8"))
        candidate = Path(str(payload.get("last_project_root") or "")).expanduser()
    except (json.JSONDecodeError, OSError, TypeError):
        return fallback
    if not candidate.exists():
        return fallback
    return candidate.resolve()


def save_last_project_root(
    project_root: Path, app_state_path: Path | None = None
) -> None:
    app_state_path = Path(app_state_path or APP_STATE_PATH)
    app_state_path.parent.mkdir(parents=True, exist_ok=True)
    state = AppState(last_project_root=str(Path(project_root).resolve()))
    app_state_path.write_text(
        json.dumps({"last_project_root": state.last_project_root}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


class SettingsService:
    def __init__(self, settings_path: Path | None = None, project_root: Path | None = None):
        resolved_root = (
            load_last_project_root() if project_root is None else Path(project_root)
        )
        self.project_root = resolved_root
        self.settings_path = (
            Path(settings_path)
            if settings_path is not None
            else project_settings_path(self.project_root)
        )

    def load(self) -> SettingsLoadResult:
        defaults = build_default_settings(self.project_root)
        if not self.settings_path.exists():
            self.save(defaults)
            return SettingsLoadResult(settings=defaults, migrated=True)

        issues: list[SettingsIssue] = []
        try:
            payload = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            self._backup_invalid_file()
            payload = {}
            issues.append(SettingsIssue("settings", f"配置文件无法读取，已恢复默认值：{exc}"))
        if not isinstance(payload, dict):
            self._backup_invalid_file()
            payload = {}
            issues.append(SettingsIssue("settings", "配置文件必须是对象，已恢复默认值"))

        migrated = int(payload.get("schema_version", 0) or 0) != 1
        self._migrate_model_export_output(payload)
        payload["schema_version"] = 1
        payload.setdefault("project", {})["root"] = str(self.project_root)
        merged = deep_merge(settings_to_dict(defaults), payload)
        merged = deserialize_settings_from_storage(merged, self.project_root)
        settings, decode_issues = settings_from_dict(merged, defaults)
        issues.extend(decode_issues)
        if issues or migrated:
            self._backup_invalid_file() if issues else None
        self.save(settings)
        return SettingsLoadResult(
            settings=settings,
            migrated=migrated,
            issues=tuple(issues),
        )

    def _migrate_model_export_output(self, payload: dict[str, Any]) -> None:
        model_export = payload.get("model_export")
        if not isinstance(model_export, dict):
            return
        current = str(model_export.get("output_dir") or "").strip()
        if not current:
            return
        current_path = Path(current).expanduser()
        if not current_path.is_absolute():
            current_path = self.project_root / current_path
        legacy = (self.project_root / "result" / "model_exports").resolve()
        if current_path.resolve() == legacy:
            model_export["output_dir"] = str(
                self.project_root / "data" / "models" / "model_exports"
            )

    def reset_to_defaults(self) -> AppSettings:
        defaults = build_default_settings(self.project_root)
        self.save(defaults)
        return defaults

    def save(self, settings: AppSettings) -> None:
        if not isinstance(settings, AppSettings):
            raise TypeError("SettingsService.save() 只接受 AppSettings")
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        data = settings_to_dict(settings)
        data["schema_version"] = 1
        serialized = serialize_settings_for_storage(data, self.project_root)
        self.settings_path.write_text(
            json.dumps(serialized, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        save_last_project_root(self.project_root)

    def _backup_invalid_file(self) -> None:
        backup = self.settings_path.with_suffix(self.settings_path.suffix + ".invalid")
        if backup.exists() or not self.settings_path.exists():
            return
        try:
            backup.write_bytes(self.settings_path.read_bytes())
        except OSError:
            return


__all__ = [
    "APP_STATE_PATH",
    "AppState",
    "PROJECT_PATH_FIELDS",
    "SettingsLoadResult",
    "SettingsService",
    "build_default_settings",
    "deep_merge",
    "deserialize_settings_from_storage",
    "load_last_project_root",
    "project_settings_path",
    "save_last_project_root",
    "serialize_settings_for_storage",
]
