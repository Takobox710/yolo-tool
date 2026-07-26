from pathlib import Path
from types import SimpleNamespace


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
    model_export_package.build_model_export_archive(
        staging,
        output,
        version="v1",
    )
    assert commands
    assert "-m0=lzma2" in commands[0]
    assert "-mmt=on" in commands[0]
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
