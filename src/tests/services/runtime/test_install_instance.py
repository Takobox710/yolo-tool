from __future__ import annotations


def test_install_instance_id_is_stable_and_settings_are_readable(tmp_path):
    from src.services.runtime.install_instance import (
        instance_id_for_path,
        installed_instance_id,
        load_install_instance,
        write_install_instance,
    )

    instance_id = instance_id_for_path(tmp_path)
    write_install_instance(
        tmp_path,
        app_version="1.3.0",
        runtime_version="runtime-2",
        base_package_version="base-runtime-models-2",
        model_bundle_version="models-2",
        model_export_version="model-export-runtime-2",
    )

    payload = load_install_instance(tmp_path)
    assert len(instance_id) == 32
    assert payload["instance_id"] == instance_id
    assert payload["app_version"] == "1.3.0"
    assert payload["model_export_installed"] == "true"
    assert payload["model_export_version"] == "model-export-runtime-2"
    assert installed_instance_id(tmp_path) == instance_id
    assert (tmp_path / "_internal" / "yolotool_metadata" / "install-instance.ini").is_file()
    assert not (tmp_path / "install-instance.ini").exists()


def test_extensions_are_scoped_by_install_instance(tmp_path):
    from src.services.runtime.install_instance import instance_extensions_root

    local = tmp_path / "local"
    first = instance_extensions_root(tmp_path / "app-one", local_app_data=local)
    second = instance_extensions_root(tmp_path / "app-two", local_app_data=local)

    assert first != second
    assert first.parent.name != second.parent.name
    assert first.name == second.name == "extensions"


def test_legacy_extension_migration_is_atomic_and_does_not_replace_target(tmp_path):
    from src.services.runtime.install_instance import (
        instance_extensions_root,
        legacy_extensions_root,
        migrate_legacy_extensions,
    )

    app_root = tmp_path / "app"
    local = tmp_path / "local"
    legacy = legacy_extensions_root(local)
    legacy.mkdir(parents=True)
    (legacy / "legacy.txt").write_text("legacy", encoding="utf-8")

    assert migrate_legacy_extensions(app_root, local_app_data=local) is True
    target = instance_extensions_root(app_root, local_app_data=local)
    assert (target / "legacy.txt").read_text(encoding="utf-8") == "legacy"
    assert not legacy.exists()

    legacy.mkdir(parents=True)
    assert migrate_legacy_extensions(app_root, local_app_data=local) is False
    assert legacy.exists()
