from __future__ import annotations

import json
from pathlib import Path

import pytest
import py7zr


def test_runtime_compatibility_requires_matching_manifests(tmp_path):
    from src.services.runtime.release_manifest import check_runtime_compatibility

    metadata = tmp_path / "_internal" / "yolotool_metadata"
    metadata.mkdir(parents=True)
    (metadata / "release-manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "app_version": "1.3.3",
                "runtime_version": "runtime-2",
                "required_runtime_version": "runtime-2",
            }
        ),
        encoding="utf-8",
    )
    (metadata / "runtime-manifest.json").write_text(
        json.dumps({"schema_version": 1, "runtime_version": "runtime-1"}),
        encoding="utf-8",
    )

    result = check_runtime_compatibility(tmp_path, frozen=True)

    assert result.compatible is False
    assert "runtime-1" in result.reason
    assert "runtime-2" in result.reason


def test_manifest_paths_fall_back_to_legacy_root_files(tmp_path):
    from src.services.runtime.release_manifest import load_release_manifest

    legacy = {"schema_version": 1, "required_runtime_version": "runtime-1"}
    (tmp_path / "release-manifest.json").write_text(
        json.dumps(legacy), encoding="utf-8"
    )

    assert load_release_manifest(tmp_path) == legacy


def test_manifest_paths_reject_traversal_and_absolute_paths():
    from src.services.runtime.release_manifest import (
        ReleaseManifestError,
        validate_relative_path,
    )

    for value in ("../outside.dll", "/absolute.dll", "C:/outside.dll", "folder/../x.dll"):
        with pytest.raises(ReleaseManifestError):
            validate_relative_path(value)

    assert validate_relative_path("folder\\file.dll") == "folder/file.dll"


def test_release_package_builds_program_without_runtime_or_user_data(tmp_path):
    from src.devtools.release_package import build_program_package

    app_root = tmp_path / "app"
    (app_root / "_internal").mkdir(parents=True)
    (app_root / "app_assets").mkdir()
    (app_root / "data" / "models").mkdir(parents=True)
    (app_root / "data" / "runtime").mkdir(parents=True)
    (app_root / "YOLOTool.exe").write_bytes(b"exe")
    (app_root / "_internal" / "torch.dll").write_bytes(b"torch")
    (app_root / "app_assets" / "app_icon.png").write_bytes(b"icon")
    (app_root / "data" / "models" / "model.pt").write_bytes(b"model")
    (app_root / "data" / "runtime" / "settings.json").write_text("{}", encoding="utf-8")

    output = tmp_path / "update"
    build_program_package(
        app_root,
        output,
        app_version="1.3.3",
        required_runtime_version="runtime-1",
    )

    assert (output / "YOLOTool.exe").exists()
    assert not (output / "app_assets").exists()
    assert not (output / "_internal").exists()
    assert not (output / "data").exists()
    assert (output / "release-manifest.json").exists()
    assert not (output / "runtime-manifest.json").exists()
    assert (output / "program-package-info.ini").exists()
    release = json.loads((output / "release-manifest.json").read_text(encoding="utf-8"))
    assert release["schema_version"] == 2
    assert release["required_runtime_version"] == "runtime-1"
    assert "runtime_files" not in release


def test_base_runtime_layer_contains_environment_and_managed_models(tmp_path):
    from src.devtools.release_package import (
        BASE_MANIFEST_NAME,
        MANAGED_MODELS_NAME,
        build_base_runtime_layer,
    )

    app_root = tmp_path / "app"
    (app_root / "_internal").mkdir(parents=True)
    (app_root / "data" / "models").mkdir(parents=True)
    (app_root / "_internal" / "torch.dll").write_bytes(b"torch")
    for name in (
        "yolo11s.pt",
        "yolo26n.pt",
        "yolov8n.pt",
        "sam2.1_hiera_base_plus.pt",
    ):
        (app_root / "data" / "models" / name).write_bytes(b"model")

    layer = tmp_path / "base-layer"
    manifest_path = build_base_runtime_layer(
        app_root,
        layer,
        package_version="v1",
        runtime_version="runtime-1",
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    managed = json.loads((layer / MANAGED_MODELS_NAME).read_text(encoding="utf-8"))
    runtime = json.loads((layer / "runtime-manifest.json").read_text(encoding="utf-8"))
    assert manifest_path.name == BASE_MANIFEST_NAME
    assert manifest["package_id"] == "yolo-tool-base-runtime-models"
    assert manifest["runtime_version"] == "runtime-1"
    assert "_internal/torch.dll" in manifest["files"]
    assert "data/models/yolo26n.pt" in manifest["files"]
    assert managed["files"] == [
        "sam2.1_hiera_base_plus.pt",
        "yolo11s.pt",
        "yolo26n.pt",
        "yolov8n.pt",
    ]
    assert "files" not in runtime
    assert not (layer / "YOLOTool.exe").exists()


def test_cpu_base_runtime_layer_uses_tiny_sam_checkpoint(tmp_path):
    from src.devtools.release_package import build_base_runtime_layer

    app_root = tmp_path / "app"
    (app_root / "_internal").mkdir(parents=True)
    (app_root / "data" / "models").mkdir(parents=True)
    (app_root / "_internal" / "torch.dll").write_bytes(b"torch")
    for name in (
        "yolo11s.pt",
        "yolo26n.pt",
        "yolov8n.pt",
        "sam2.1_hiera_tiny.pt",
    ):
        (app_root / "data" / "models" / name).write_bytes(b"model")

    layer = tmp_path / "base-layer"
    build_base_runtime_layer(
        app_root,
        layer,
        package_version="v1",
        runtime_version="runtime-1",
        variant="cpu",
    )

    managed = json.loads((layer / "managed-models.json").read_text(encoding="utf-8"))
    assert managed["files"] == [
        "sam2.1_hiera_tiny.pt",
        "yolo11s.pt",
        "yolo26n.pt",
        "yolov8n.pt",
    ]
    assert (layer / "data" / "models" / "sam2.1_hiera_tiny.pt").is_file()
    assert not (layer / "data" / "models" / "sam2.1_hiera_base_plus.pt").exists()


def test_gpu_base_runtime_filters_extra_environment_files(monkeypatch, tmp_path):
    from src.devtools import base_runtime_builder

    app_root = tmp_path / "app"
    (app_root / "_internal" / "openvino").mkdir(parents=True)
    (app_root / "_internal" / "onnxruntime").mkdir(parents=True)
    (app_root / "data" / "models").mkdir(parents=True)
    (app_root / "_internal" / "openvino" / "runtime.pyd").write_bytes(b"extra")
    (app_root / "_internal" / "onnxruntime" / "runtime.pyd").write_bytes(b"gpu")
    cpu_root = tmp_path / "release-cpu"
    cpu_package = cpu_root / "Lib" / "site-packages" / "onnxruntime"
    cpu_package.mkdir(parents=True)
    (cpu_package / "runtime.pyd").write_bytes(b"cpu")
    (cpu_root / "Lib" / "site-packages" / "onnxruntime-1.0.dist-info").mkdir()
    for name in (
        "yolo11s.pt",
        "yolo26n.pt",
        "yolov8n.pt",
        "sam2.1_hiera_base_plus.pt",
    ):
        (app_root / "data" / "models" / name).write_bytes(b"model")

    monkeypatch.setattr(
        base_runtime_builder,
        "extension_distribution_paths",
        lambda distributions=(): {
            Path("openvino/runtime.pyd"),
            Path("onnxruntime/runtime.pyd"),
        },
    )
    monkeypatch.setattr(base_runtime_builder.metadata, "version", lambda _name: "1.0")

    layer = tmp_path / "base-layer"
    base_runtime_builder.build_base_runtime_layer(
        app_root,
        layer,
        package_version="v1",
        runtime_version="runtime-1",
        variant="gpu",
        cpu_runtime_root=cpu_root,
    )

    assert not (layer / "_internal" / "openvino" / "runtime.pyd").exists()
    assert (layer / "_internal" / "onnxruntime" / "runtime.pyd").read_bytes() == b"cpu"


def test_cpu_base_runtime_keeps_integrated_export_files(tmp_path):
    from src.devtools import base_runtime_builder

    app_root = tmp_path / "app"
    (app_root / "_internal" / "openvino").mkdir(parents=True)
    (app_root / "data" / "models").mkdir(parents=True)
    (app_root / "_internal" / "openvino" / "runtime.pyd").write_bytes(b"cpu")
    for name in (
        "yolo11s.pt",
        "yolo26n.pt",
        "yolov8n.pt",
        "sam2.1_hiera_tiny.pt",
    ):
        (app_root / "data" / "models" / name).write_bytes(b"model")

    layer = tmp_path / "base-layer"
    base_runtime_builder.build_base_runtime_layer(
        app_root,
        layer,
        package_version="v1",
        runtime_version="runtime-1",
        variant="cpu",
    )

    assert (layer / "_internal" / "openvino" / "runtime.pyd").exists()


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

    archive_path = build_base_runtime_archive(
        app_root,
        tmp_path / "staging",
        tmp_path / "output",
        package_version="v1",
        runtime_version="runtime-1",
    )

    assert archive_path.name == "YOLOTool_BaseEnv_v1.7z"
    assert (tmp_path / "output" / "YOLOTool_BaseEnv_v1.7z").exists()
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

    archive_path = build_base_runtime_archive(
        app_root,
        tmp_path / "staging",
        tmp_path / "output",
        package_version="v1",
        runtime_version="runtime-1",
        split=True,
    )

    assert archive_path.name == "YOLOTool_BaseEnv_v1.7z.001"
    assert archive_path.is_file()


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
