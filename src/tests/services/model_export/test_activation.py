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


def test_gpu_ort_overlay_is_preferred_when_probe_succeeds(monkeypatch, tmp_path):
    from src.services.model_export import activation
    from src.services.model_export.types import InstalledExtension

    package_root = tmp_path / "packages"
    gpu_root = package_root / "_onnxruntime_gpu"
    (gpu_root / "onnxruntime" / "capi").mkdir(parents=True)
    package_root.mkdir(exist_ok=True)
    installed = InstalledExtension(
        version="v3",
        root=tmp_path,
        package_dir=package_root,
        supported_formats=("openvino", "engine", "ncnn"),
        manifest={
            "runtime_overlays": {"onnxruntime_gpu": "_onnxruntime_gpu"},
            "dll_dirs": [],
        },
    )
    monkeypatch.setattr(activation, "_gpu_ort_available", lambda _root: True)
    original = list(sys.path)
    try:
        activation.activate_extension(installed)
        assert sys.path[0] == str(gpu_root.resolve())
    finally:
        sys.path[:] = original
