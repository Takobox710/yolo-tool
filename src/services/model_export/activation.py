from __future__ import annotations

import os
import sys
from pathlib import Path

from src.services.model_export.package import (
    PROBE_EXTENSION_ROOT_ENV,
    load_extension_at,
    load_installed_extension,
)
from src.services.model_export.types import InstalledExtension
from src.services.runtime.variant import CPU_VARIANT, installed_variant


_DLL_HANDLES: list[object] = []


def activate_installed_extension(base_root: Path | None = None) -> bool:
    if installed_variant() == CPU_VARIANT:
        return False
    candidate_root = os.environ.get(PROBE_EXTENSION_ROOT_ENV, "").strip()
    installed = (
        load_extension_at(Path(candidate_root))
        if candidate_root
        else load_installed_extension(base_root)
    )
    if installed is None:
        return False
    activate_extension(installed)
    return True


def activate_extension(installed: InstalledExtension) -> None:
    package_dir = installed.package_dir.resolve()
    package_text = str(package_dir)
    if package_text not in sys.path:
        sys.path.append(package_text)
    dll_paths: list[str] = []
    for relative in installed.manifest.get("dll_dirs", ()):
        dll_dir = installed.root / Path(str(relative))
        if not dll_dir.is_dir():
            continue
        dll_text = str(dll_dir.resolve())
        dll_paths.append(dll_text)
        if os.name == "nt" and hasattr(os, "add_dll_directory"):
            _DLL_HANDLES.append(os.add_dll_directory(dll_text))
    if dll_paths:
        os.environ["PATH"] = os.pathsep.join([*dll_paths, os.environ.get("PATH", "")])
