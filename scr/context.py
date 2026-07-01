from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ServiceContainer:
    settings: Any
    annotation: Any
    conversion: Any
    detection: Any
    environment: Any
    rename: Any
    resize: Any
    runtime: Any
    training: Any


@dataclass(slots=True)
class AppContext:
    project_root: Path
    settings: dict[str, Any]
    services: ServiceContainer
