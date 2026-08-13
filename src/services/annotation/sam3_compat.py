from __future__ import annotations

import importlib.resources
import sys
import warnings
from pathlib import PurePosixPath
from types import ModuleType
from typing import Any


def load_sam3_components() -> tuple[type[Any], Any]:
    compat_module = None
    try:
        import pkg_resources  # noqa: F401
    except ModuleNotFoundError as exc:
        if exc.name != "pkg_resources":
            raise
        compat_module = ModuleType("pkg_resources")
        compat_module.resource_filename = _resource_filename
        sys.modules["pkg_resources"] = compat_module
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r"`torch\.jit\.script` is deprecated.*",
                category=DeprecationWarning,
                module=r"torch\.jit\._script",
            )
            warnings.filterwarnings(
                "ignore",
                message=r"Importing from timm\.models\.layers is deprecated.*",
                category=FutureWarning,
                module=r"timm\.models\.layers",
            )
            from sam3.model.sam3_image_processor import Sam3Processor
            from sam3.model_builder import build_sam3_image_model
    finally:
        if compat_module is not None and sys.modules.get("pkg_resources") is compat_module:
            del sys.modules["pkg_resources"]
    return Sam3Processor, build_sam3_image_model


def _resource_filename(package: str, resource_name: str) -> str:
    resource = importlib.resources.files(package)
    for part in PurePosixPath(resource_name).parts:
        resource = resource.joinpath(part)
    return str(resource)


__all__ = ["load_sam3_components"]
