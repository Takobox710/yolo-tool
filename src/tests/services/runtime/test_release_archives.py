from __future__ import annotations

import json
from pathlib import Path

import pytest
import py7zr

def test_base_runtime_archive_excludes_program_and_uses_expected_name(tmp_path):
    from src.devtools.release_package import build_base_runtime_archive

    app_root = tmp_path / "app"
    (app_root / "_internal").mkdir(parents=True)
    (app_root / "data" / "models").mkdir(parents=True)
    (app_root / "YOLOTool.exe").write_bytes(b"program")
    (app_root / "_internal" / "runtime.dll").write_bytes(b"runtime")
    for name in (
        "yolo11s.pt",
        "yolo26n.pt",
        "yolov8n.pt",
        "sam2.1_hiera_base_plus.pt",
    ):
        (app_root / "data" / "models" / name).write_bytes(b"model")

    output = tmp_path / "output"
    output.mkdir()
    split_marker = output / "YOLOTool_BaseEnv_v1.7z.001"
    split_marker.write_bytes(b"existing split volume")
    archive_path = build_base_runtime_archive(
        app_root,
        tmp_path / "staging",
        output,
        package_version="v1",
        runtime_version="runtime-1",
    )

    assert archive_path.name == "YOLOTool_BaseEnv_v1.7z"
    assert (tmp_path / "output" / "YOLOTool_BaseEnv_v1.7z").exists()
    assert split_marker.is_file()
    with py7zr.SevenZipFile(archive_path, "r") as archive:
        names = set(archive.getnames())
    assert "_internal/runtime.dll" in names
    assert "data/models/yolo26n.pt" in names
    assert "YOLOTool.exe" not in names

def test_base_runtime_archive_can_use_split_volumes_when_requested(tmp_path):
    from src.devtools.release_package import build_base_runtime_archive

    app_root = tmp_path / "app"
    (app_root / "_internal").mkdir(parents=True)
    (app_root / "data" / "models").mkdir(parents=True)
    (app_root / "_internal" / "runtime.dll").write_bytes(b"runtime")
    for name in (
        "yolo11s.pt",
        "yolo26n.pt",
        "yolov8n.pt",
        "sam2.1_hiera_base_plus.pt",
    ):
        (app_root / "data" / "models" / name).write_bytes(b"model")

    output = tmp_path / "output"
    output.mkdir()
    single_marker = output / "YOLOTool_BaseEnv_v1.7z"
    single_marker.write_bytes(b"existing single archive")
    archive_path = build_base_runtime_archive(
        app_root,
        tmp_path / "staging",
        output,
        package_version="v1",
        runtime_version="runtime-1",
        split=True,
    )

    assert archive_path.name == "YOLOTool_BaseEnv_v1.7z.001"
    assert archive_path.is_file()
    assert single_marker.is_file()

def test_base_runtime_archive_always_rebuilds_without_cache(tmp_path):
    from src.devtools.release_package import build_base_runtime_archive

    app_root = tmp_path / "app"
    (app_root / "_internal").mkdir(parents=True)
    (app_root / "data" / "models").mkdir(parents=True)
    (app_root / "_internal" / "runtime.dll").write_bytes(b"runtime")
    for name in (
        "yolo11s.pt",
        "yolo26n.pt",
        "yolov8n.pt",
        "sam2.1_hiera_base_plus.pt",
    ):
        (app_root / "data" / "models" / name).write_bytes(b"model")

    staging = tmp_path / "staging"
    output = tmp_path / "output"
    build_base_runtime_archive(
        app_root,
        staging,
        output,
        package_version="v1",
        runtime_version="runtime-1",
    )
    cache_path = output / "YOLOTool_BaseEnv_v1.7z.cache.json"
    assert not cache_path.exists()
    marker = staging / "keep-on-cache-hit.txt"
    marker.write_text("cached", encoding="utf-8")

    build_base_runtime_archive(
        app_root,
        staging,
        output,
        package_version="v1",
        runtime_version="runtime-1",
    )
    assert not marker.exists()
    assert not cache_path.exists()
