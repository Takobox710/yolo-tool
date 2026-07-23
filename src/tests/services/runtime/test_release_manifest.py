from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_runtime_compatibility_requires_matching_manifests(tmp_path):
    from src.services.runtime.release_manifest import check_runtime_compatibility

    (tmp_path / "release-manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "app_version": "1.3.0",
                "runtime_version": "runtime-2",
                "required_runtime_version": "runtime-2",
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "runtime-manifest.json").write_text(
        json.dumps({"schema_version": 1, "runtime_version": "runtime-1", "files": {}}),
        encoding="utf-8",
    )

    result = check_runtime_compatibility(tmp_path, frozen=True)

    assert result.compatible is False
    assert "runtime-1" in result.reason
    assert "runtime-2" in result.reason


def test_manifest_paths_reject_traversal_and_absolute_paths():
    from src.services.runtime.release_manifest import (
        ReleaseManifestError,
        validate_relative_path,
    )

    for value in ("../outside.dll", "/absolute.dll", "C:/outside.dll", "folder/../x.dll"):
        with pytest.raises(ReleaseManifestError):
            validate_relative_path(value)

    assert validate_relative_path("folder\\file.dll") == "folder/file.dll"


def test_release_package_builds_app_update_without_runtime_or_user_data(tmp_path):
    from src.devtools.release_package import build_package

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
    build_package(
        app_root,
        output,
        package_type="AppUpdate",
        app_version="1.3.0",
        runtime_version="runtime-1",
        required_runtime_version="runtime-1",
    )

    assert (output / "YOLOTool.exe").exists()
    assert (output / "app_assets" / "app_icon.png").exists()
    assert not (output / "_internal").exists()
    assert not (output / "data").exists()
    assert (output / "release-manifest.json").exists()
    assert (output / "package-info.ini").exists()


def test_release_package_supports_full_and_runtime_upgrade_layers(tmp_path):
    from src.devtools.release_package import build_package

    app_root = tmp_path / "app"
    (app_root / "_internal").mkdir(parents=True)
    (app_root / "data" / "models").mkdir(parents=True)
    (app_root / "YOLOTool-dev.exe").write_bytes(b"dev-exe")
    (app_root / "_internal" / "torch.dll").write_bytes(b"torch")
    (app_root / "data" / "models" / "model.pt").write_bytes(b"model")

    full = tmp_path / "full"
    build_package(
        app_root,
        full,
        package_type="Full",
        app_version="1.3.0",
        runtime_version="runtime-1",
        required_runtime_version="runtime-1",
        exe_name="YOLOTool-dev.exe",
    )
    runtime_full = tmp_path / "runtime-full"
    build_package(
        app_root,
        runtime_full,
        package_type="RuntimeFull",
        app_version="1.3.0",
        runtime_version="runtime-2",
        required_runtime_version="runtime-2",
        exe_name="YOLOTool-dev.exe",
    )

    assert (full / "YOLOTool-dev.exe").exists()
    assert (full / "_internal" / "torch.dll").exists()
    assert (full / "data" / "models" / "model.pt").exists()
    assert (runtime_full / "_internal" / "torch.dll").exists()
    assert (runtime_full / "YOLOTool-dev.exe").exists()
    assert not (runtime_full / "data").exists()
