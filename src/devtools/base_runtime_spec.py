from __future__ import annotations

from src.services.runtime.variant import normalize_variant

BASE_PACKAGE_SCHEMA_VERSION = 1
BASE_PACKAGE_ID = "yolo-tool-base-runtime-models"
BASE_MANIFEST_NAME = "base-package-manifest.json"
MANAGED_MODELS_NAME = "managed-models.json"
GPU_BASE_MODEL_NAMES = ("yolo11s.pt", "yolo26n.pt", "yolov8n.pt", "sam2.1_hiera_base_plus.pt")
CPU_BASE_MODEL_NAMES = ("yolo11s.pt", "yolo26n.pt", "yolov8n.pt", "sam2.1_hiera_tiny.pt")
BASE_MODEL_NAMES = GPU_BASE_MODEL_NAMES
STDLIB_ARCHIVE_NAME = "python_stdlib.zip"
BASE_ARCHIVE_VOLUME_BYTES = 1_073_700_000
BASE_ARCHIVE_VOLUME_COUNT = 2


def base_model_names_for_variant(variant: str) -> tuple[str, ...]:
    return CPU_BASE_MODEL_NAMES if normalize_variant(variant) == "cpu" else GPU_BASE_MODEL_NAMES


__all__ = [name for name in globals() if name.startswith("BASE_") or name.endswith("MODEL_NAMES") or name in {"MANAGED_MODELS_NAME", "STDLIB_ARCHIVE_NAME", "base_model_names_for_variant"}]
