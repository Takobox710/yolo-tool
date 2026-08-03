from pathlib import Path
from types import SimpleNamespace

import pytest


def test_collector_copies_only_safe_distribution_files(monkeypatch, tmp_path):
    from src.devtools import model_export_package

    source = tmp_path / "source"
    (source / "backend").mkdir(parents=True)
    (source / "backend" / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "optional-1.0.dist-info").mkdir()
    (source / "optional-1.0.dist-info" / "METADATA").write_text(
        "Name: optional\nVersion: 1.0\n", encoding="utf-8"
    )

    class FakeDistribution:
        version = "1.0"
        files = [
            Path("backend/__init__.py"),
            Path("optional-1.0.dist-info/METADATA"),
            Path("../../Scripts/optional.exe"),
        ]

        @staticmethod
        def locate_file(item):
            return source / item

    monkeypatch.setattr(
        model_export_package.metadata,
        "distribution",
        lambda _name: FakeDistribution(),
    )
    target = tmp_path / "packages"
    versions = model_export_package.collect_optional_distributions(
        target, ("optional",)
    )

    assert versions == {"optional": "1.0"}
    assert (target / "backend" / "__init__.py").is_file()
    assert (target / "optional-1.0.dist-info" / "METADATA").is_file()
    assert not (target / "Scripts").exists()


def test_collector_places_gpu_onnxruntime_under_isolated_overlay(monkeypatch, tmp_path):
    from src.devtools import model_export_package

    source = tmp_path / "source"
    (source / "onnxruntime" / "capi").mkdir(parents=True)
    (source / "onnxruntime" / "capi" / "onnxruntime_providers_cuda.dll").write_bytes(
        b"cuda"
    )

    class FakeDistribution:
        version = "1.28.0"
        files = [Path("onnxruntime/capi/onnxruntime_providers_cuda.dll")]

        @staticmethod
        def locate_file(item):
            return source / item

    monkeypatch.setattr(
        model_export_package.metadata,
        "distribution",
        lambda _name: FakeDistribution(),
    )
    target = tmp_path / "packages"
    versions = model_export_package.collect_runtime_overlays(target)

    assert versions == {"onnxruntime_gpu": "1.28.0"}
    assert (
        target / "_onnxruntime_gpu" / "onnxruntime" / "capi" / "onnxruntime_providers_cuda.dll"
    ).read_bytes() == b"cuda"


def test_model_export_archive_always_rebuilds_without_cache(monkeypatch, tmp_path):
    from src.devtools import model_export_package

    source = tmp_path / "source"
    (source / "backend").mkdir(parents=True)
    source_file = source / "backend" / "__init__.py"
    source_file.write_text("VALUE = 1\n", encoding="utf-8")

    class FakeDistribution:
        version = "1.0"
        files = [Path("backend/__init__.py")]

        @staticmethod
        def locate_file(item):
            return source / item

    monkeypatch.setattr(model_export_package, "OPTIONAL_DISTRIBUTIONS", ("optional",))
    monkeypatch.setattr(
        model_export_package.metadata,
        "distribution",
        lambda _name: FakeDistribution(),
    )
    commands = []

    def fake_run(command, **_kwargs):
        commands.append(command)
        Path(command[3]).write_bytes(b"7z archive")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(model_export_package.shutil, "which", lambda _name: "7z.exe")
    monkeypatch.setattr(model_export_package.subprocess, "run", fake_run)

    staging = tmp_path / "staging"
    output = tmp_path / "output"
    output.mkdir()
    split_marker = output / "YOLOTool_ExtraEnv_v1.7z.001"
    split_marker.write_bytes(b"existing split volume")
    model_export_package.build_model_export_archive(
        staging,
        output,
        version="v1",
    )
    assert commands
    assert "-m0=lzma2" in commands[0]
    assert "-mmt=on" in commands[0]
    assert split_marker.is_file()
    cache_path = output / "YOLOTool_ExtraEnv_v1.7z.cache.json"
    assert not cache_path.exists()
    marker = staging / "keep-on-cache-hit.txt"
    marker.write_text("cached", encoding="utf-8")

    model_export_package.build_model_export_archive(
        staging,
        output,
        version="v1",
    )
    assert not marker.exists()
    assert not cache_path.exists()


def test_model_export_archive_can_use_split_volumes(monkeypatch, tmp_path):
    from src.devtools import model_export_package

    source = tmp_path / "source"
    (source / "backend").mkdir(parents=True)
    (source / "backend" / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")

    class FakeDistribution:
        version = "1.0"
        files = [Path("backend/__init__.py")]

        @staticmethod
        def locate_file(item):
            return source / item

    monkeypatch.setattr(model_export_package, "OPTIONAL_DISTRIBUTIONS", ("optional",))
    monkeypatch.setattr(
        model_export_package.metadata,
        "distribution",
        lambda _name: FakeDistribution(),
    )
    commands = []

    def fake_run(command, **_kwargs):
        commands.append(command)
        archive_path = Path(command[3])
        archive_path.with_name(f"{archive_path.name}.001").write_bytes(b"part 1")
        archive_path.with_name(f"{archive_path.name}.002").write_bytes(b"part 2")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(model_export_package.shutil, "which", lambda _name: "7z.exe")
    monkeypatch.setattr(model_export_package.subprocess, "run", fake_run)

    output = tmp_path / "output"
    output.mkdir()
    single_marker = output / "YOLOTool_ExtraEnv_v1.7z"
    single_marker.write_bytes(b"existing single archive")
    archive_path = model_export_package.build_model_export_archive(
        tmp_path / "staging",
        output,
        version="v1",
        split=True,
    )

    assert archive_path.name == "YOLOTool_ExtraEnv_v1.7z.001"
    assert "-v1073700000b" in commands[0]
    assert (output / "YOLOTool_ExtraEnv_v1.7z.002").is_file()
    assert single_marker.is_file()


def test_model_export_layer_rejects_files_already_owned_by_base(monkeypatch, tmp_path):
    from src.devtools import model_export_package

    source = tmp_path / "source"
    (source / "backend").mkdir(parents=True)
    (source / "backend" / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")

    class FakeDistribution:
        version = "1.0"
        files = [Path("backend/__init__.py")]

        @staticmethod
        def locate_file(item):
            return source / item

    monkeypatch.setattr(model_export_package, "OPTIONAL_DISTRIBUTIONS", ("optional",))
    monkeypatch.setattr(
        model_export_package.metadata,
        "distribution",
        lambda _name: FakeDistribution(),
    )
    base_staging = tmp_path / "base"
    base_staging.mkdir()
    (base_staging / "base-package-manifest.json").write_text(
        '{"files": ["_internal/backend/__init__.py"]}',
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="重复文件"):
        model_export_package.build_model_export_layer(
            tmp_path / "extension",
            version="v1",
            base_staging_root=base_staging,
        )
