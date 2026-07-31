from __future__ import annotations

from pathlib import Path


def test_variant_helpers_keep_cpu_and_gpu_artifacts_isolated(tmp_path, monkeypatch):
    from src.services.runtime.variant import (
        CPU_VARIANT,
        GPU_VARIANT,
        build_variant,
        installed_variant,
        variant_asset_prefix,
    )

    monkeypatch.setenv("YOLO_TOOL_BUILD_VARIANT", "CPU")
    assert build_variant() == CPU_VARIANT
    assert variant_asset_prefix(CPU_VARIANT) == "YOLOTool_CPU"
    assert variant_asset_prefix(GPU_VARIANT) == "YOLOTool"

    metadata_root = Path(tmp_path) / "_internal" / "yolotool_metadata"
    metadata_root.mkdir(parents=True)
    (metadata_root / "package-info.ini").write_text(
        "[Package]\nvariant=cpu\n", encoding="utf-8"
    )
    assert installed_variant(tmp_path) == CPU_VARIANT


def test_variant_helpers_default_invalid_values_to_gpu(monkeypatch):
    from src.services.runtime.variant import build_variant, normalize_variant

    monkeypatch.setenv("YOLO_TOOL_BUILD_VARIANT", "unknown")
    assert normalize_variant("unknown") == "gpu"
    assert build_variant() == "gpu"
