from __future__ import annotations

import json
import zipfile
from pathlib import Path

import py7zr
import pytest


def _write_package(
    path: Path,
    *,
    version: str = "runtime-1",
    extra_name: str | None = None,
    protocol_version: int = 1,
    legacy_hash_manifest: bool = False,
) -> Path:
    payload = b"runtime"
    files = (
        {"packages/backend.py": "0" * 64}
        if legacy_hash_manifest
        else ["packages/backend.py"]
    )
    manifest = {
        "schema_version": 1,
        "package_id": "yolo-tool-model-export-runtime",
        "protocol_version": protocol_version,
        "version": version,
        "platform": "win-64",
        "architecture": "x86_64",
        "package_dir": "packages",
        "supported_formats": ["engine"],
        "dll_dirs": [],
        "files": files,
    }
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("extension-manifest.json", json.dumps(manifest))
        archive.writestr("packages/backend.py", payload)
        if extra_name:
            archive.writestr(extra_name, b"extra")
    return path


def _convert_to_7z(zip_path: Path, archive_path: Path, tmp_path: Path) -> Path:
    source = tmp_path / f"layer-{archive_path.stem}"
    source.mkdir()
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(source)
    with py7zr.SevenZipFile(
        archive_path,
        "w",
        filters=[{"id": py7zr.FILTER_LZMA2, "preset": 9}],
    ) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(source).as_posix())
    return archive_path


def test_7z_extension_package_installs_from_lzma2_archive(tmp_path):
    from src.services.model_export import (
        inspect_extension_package,
        install_extension_package,
    )

    package = _convert_to_7z(
        _write_package(tmp_path / "source.zip"),
        tmp_path / "runtime.7z",
        tmp_path,
    )
    manifest = inspect_extension_package(package)
    events: list[tuple[str, int]] = []
    installed = install_extension_package(
        package,
        base_root=tmp_path / "extensions",
        probe=lambda _entry: {"protocol_version": 1, "ok": True},
        progress=lambda message, value: events.append((message, value)),
    )

    assert manifest["version"] == "runtime-1"
    assert installed.version == "runtime-1"
    values = [value for _message, value in events]
    assert values[0] == 5
    assert 5 in values
    assert 95 in values
    assert values[-1] == 100
    assert values == sorted(values)


def test_native_7z_reports_incremental_extraction_progress(tmp_path, monkeypatch):
    from src.services.model_export import native_archive

    executable = tmp_path / "7z.exe"
    executable.touch()

    class FakeStream:
        def __init__(self):
            self.chunks = iter((b" 0", b"%\r 50%", b"\r 100", b"%\r"))

        def read(self, _size):
            return next(self.chunks, b"")

        def close(self):
            return None

    class FakeProcess:
        def __init__(self):
            self.stdout = FakeStream()

        def wait(self, timeout=None):
            return 0

    command: list[str] = []

    monkeypatch.setattr(native_archive, "find_native_7z", lambda: executable)
    monkeypatch.setattr(
        native_archive.subprocess,
        "Popen",
        lambda *args, **kwargs: (command.extend(args[0]), FakeProcess())[1],
    )

    values: list[int] = []
    native_archive.extract_archive(
        tmp_path / "runtime.7z",
        tmp_path / "destination",
        progress=values.append,
    )

    assert values == [0, 50, 100]
    assert "-bsp1" in command
    assert "-bd" not in command


def test_7z_install_uses_archive_crc_without_file_hash_pass(tmp_path):
    from src.services.model_export import install_extension_package

    package = _convert_to_7z(
        _write_package(tmp_path / "source.zip"),
        tmp_path / "runtime.7z",
        tmp_path,
    )
    installed = install_extension_package(
        package,
        base_root=tmp_path / "extensions",
        probe=lambda _entry: {"protocol_version": 1, "ok": True},
    )

    assert installed.version == "runtime-1"


def test_extension_package_installs_and_switches_active_version(tmp_path):
    from src.services.model_export import install_extension_package, load_installed_extension

    base = tmp_path / "extensions"
    probe = lambda _entry: {"protocol_version": 1, "ok": True}
    first = install_extension_package(
        _write_package(tmp_path / "one.zip"), base_root=base, probe=probe
    )
    second = install_extension_package(
        _write_package(tmp_path / "two.zip", version="runtime-2"),
        base_root=base,
        probe=probe,
    )

    active = load_installed_extension(base)
    assert first.version == "runtime-1"
    assert second.version == "runtime-2"
    assert active is not None and active.version == "runtime-2"
    assert (base / "model-export-runtime" / "runtime-1").is_dir()
    assert (base / "model-export-runtime" / "active.ini").is_file()


def test_legacy_hashed_manifest_is_read_without_hash_validation(tmp_path):
    from src.services.model_export import install_extension_package

    installed = install_extension_package(
        _write_package(
            tmp_path / "legacy.zip",
            legacy_hash_manifest=True,
        ),
        base_root=tmp_path / "extensions",
        probe=lambda _entry: {"protocol_version": 1, "ok": True},
    )

    assert installed.manifest["files"] == ["packages/backend.py"]


def test_extension_package_rejects_unlisted_files(tmp_path):
    from src.services.model_export import ExtensionPackageError, install_extension_package

    probe = lambda _entry: {"protocol_version": 1, "ok": True}
    extra = _write_package(tmp_path / "extra.zip", extra_name="packages/unlisted.dll")
    with pytest.raises(ExtensionPackageError, match="未登记文件"):
        install_extension_package(extra, base_root=tmp_path / "extra-root", probe=probe)


def test_extension_package_rejects_path_traversal(tmp_path):
    from src.services.model_export import ExtensionPackageError, install_extension_package

    package = _write_package(tmp_path / "traversal.zip", extra_name="../outside.dll")
    with pytest.raises(ExtensionPackageError, match="不安全路径"):
        install_extension_package(
            package,
            base_root=tmp_path / "root",
            probe=lambda _entry: {"protocol_version": 1, "ok": True},
        )
    assert not (tmp_path / "outside.dll").exists()


def test_7z_extension_package_rejects_path_traversal(tmp_path, monkeypatch):
    from src.services.model_export import ExtensionPackageError, inspect_extension_package
    from src.services.model_export import package as package_service

    class UnsafeEntry:
        filename = "../outside.dll"
        is_symlink = False
        is_directory = False

    class UnsafeArchive:
        def __init__(self, *_args, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def list(self):
            return [UnsafeEntry()]

    package = tmp_path / "traversal.7z"
    package.touch()
    monkeypatch.setattr(package_service.py7zr, "SevenZipFile", UnsafeArchive)

    with pytest.raises(ExtensionPackageError, match="不安全路径"):
        inspect_extension_package(package)
    assert not (tmp_path / "outside.dll").exists()


def test_extension_package_rejects_protocol_mismatch(tmp_path):
    from src.services.model_export import ExtensionPackageError, install_extension_package

    package = _write_package(tmp_path / "protocol.zip", protocol_version=99)
    with pytest.raises(ExtensionPackageError, match="协议"):
        install_extension_package(
            package,
            base_root=tmp_path / "root",
            probe=lambda _entry: {"protocol_version": 1, "ok": True},
        )


def test_probe_failure_keeps_active_version(tmp_path):
    from src.services.model_export import (
        ExtensionPackageError,
        install_extension_package,
        load_installed_extension,
    )

    base = tmp_path / "extensions"
    install_extension_package(
        _write_package(tmp_path / "one.zip"),
        base_root=base,
        probe=lambda _entry: {"protocol_version": 1, "ok": True},
    )

    def fail_probe(_entry):
        raise ExtensionPackageError("probe failed")

    with pytest.raises(ExtensionPackageError, match="probe failed"):
        install_extension_package(
            _write_package(tmp_path / "two.zip", version="runtime-2"),
            base_root=base,
            probe=fail_probe,
        )

    active = load_installed_extension(base)
    assert active is not None and active.version == "runtime-1"
    assert not (base / "model-export-runtime" / "runtime-2").exists()


def test_extension_keeps_only_current_and_previous_versions(tmp_path):
    from src.services.model_export import install_extension_package

    base = tmp_path / "extensions"
    probe = lambda _entry: {"protocol_version": 1, "ok": True}
    for index in range(1, 4):
        install_extension_package(
            _write_package(tmp_path / f"{index}.zip", version=f"runtime-{index}"),
            base_root=base,
            probe=probe,
        )
    root = base / "model-export-runtime"
    assert not (root / "runtime-1").exists()
    assert (root / "runtime-2").is_dir()
    assert (root / "runtime-3").is_dir()
