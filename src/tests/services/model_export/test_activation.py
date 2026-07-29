import json
import sys


def test_installed_extension_adds_package_directory_to_sys_path(tmp_path):
    from src.services.model_export import activate_installed_extension

    root = tmp_path / "model-export-runtime"
    version_root = root / "runtime-1"
    package_root = version_root / "packages"
    package_root.mkdir(parents=True)
    module = package_root / "optional_backend.py"
    module.write_text("VALUE = 1\n", encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "package_id": "yolo-tool-model-export-runtime",
        "protocol_version": 1,
        "version": "runtime-1",
        "platform": "win-64",
        "architecture": "x86_64",
        "package_dir": "packages",
        "supported_formats": ["openvino"],
        "dll_dirs": [],
        "files": ["packages/optional_backend.py"],
    }
    (version_root / "extension-manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    (root / "active.json").write_text(
        json.dumps({"active_version": "runtime-1"}), encoding="utf-8"
    )

    original = list(sys.path)
    try:
        assert activate_installed_extension(tmp_path)
        assert str(package_root.resolve()) in sys.path
    finally:
        sys.path[:] = original
