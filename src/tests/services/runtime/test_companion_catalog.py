from __future__ import annotations

import json

import py7zr


def _build_base_archive(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    manifest = {
        "schema_version": 1,
        "package_id": "yolo-tool-base-runtime-models",
        "version": "base-runtime-models-1",
        "runtime_version": "runtime-1",
        "platform": "win-64",
        "architecture": "x86_64",
        "uncompressed_size": 1234,
        "files": {},
    }
    (source / "base-package-manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    archive_path = tmp_path / "base.7z"
    with py7zr.SevenZipFile(archive_path, "w") as archive:
        archive.write(
            source / "base-package-manifest.json", "base-package-manifest.json"
        )
    return archive_path


def test_companion_catalog_records_base_version_without_archive_identity(tmp_path):
    from src.devtools.companion_catalog import build_companion_catalog

    archive_path = _build_base_archive(tmp_path)

    catalog = build_companion_catalog(archive_path)

    assert catalog == {
        "schema_version": 1,
        "base": {
            "filename": "base.7z",
            "package_id": "yolo-tool-base-runtime-models",
            "manifest_schema": 1,
            "platform": "win-64",
            "architecture": "x86_64",
            "version": "base-runtime-models-1",
            "runtime_version": "runtime-1",
            "uncompressed_size": 1234,
        },
    }


def test_companion_catalog_rejects_wrong_base_package_identity(tmp_path):
    from src.devtools.companion_catalog import inspect_base_archive

    archive_path = _build_base_archive(tmp_path)
    extracted = tmp_path / "rewrite"
    with py7zr.SevenZipFile(archive_path, "r") as archive:
        archive.extractall(extracted)
    payload = json.loads(
        (extracted / "base-package-manifest.json").read_text(encoding="utf-8")
    )
    payload["package_id"] = "wrong-package"
    (extracted / "base-package-manifest.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    archive_path.unlink()
    with py7zr.SevenZipFile(archive_path, "w") as archive:
        archive.write(
            extracted / "base-package-manifest.json", "base-package-manifest.json"
        )

    try:
        inspect_base_archive(archive_path)
    except ValueError as exc:
        assert "不是 YOLOTool 基础环境" in str(exc)
    else:
        raise AssertionError("wrong package identity was accepted")
