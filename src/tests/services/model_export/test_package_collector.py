from pathlib import Path


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
