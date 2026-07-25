from pathlib import Path


def test_model_export_dependencies_are_split_between_pixi_environments():
    manifest = Path("pixi.toml").read_text(encoding="utf-8")

    assert "[feature.release-base.pypi-dependencies]" in manifest
    assert "onnxruntime =" in manifest
    assert "[feature.export-full.pypi-dependencies]" in manifest
    assert "onnxruntime-gpu =" in manifest
    assert 'openvino = ">=2026.2.1, <2027"' in manifest
    assert 'ncnn = ">=1.0.20260526"' in manifest
    assert 'pnnx = ">=20260526"' in manifest
    assert "tensorrt-cu13-libs" in manifest
    assert 'py7zr = ' in manifest
    assert 'default = ["export-full"]' in manifest


def test_model_export_runtime_build_contract_is_present():
    base_spec = Path("installer/YOLOTool.spec").read_text(encoding="utf-8")
    build_script = Path("installer/build_model_export_runtime.ps1").read_text(encoding="utf-8")
    collector = Path("src/devtools/model_export_package.py").read_text(encoding="utf-8")

    for package in ("openvino", "ncnn", "pnnx", "tensorrt"):
        assert f'"{package}"' in base_spec
    optional_block = collector.split("OPTIONAL_DISTRIBUTIONS", 1)[1].split(")", 1)[0]
    assert '"tensorrt"' in optional_block
    for package in ("openvino", "openvino-telemetry", "ncnn", "pnnx", "tqdm", "portalocker"):
        assert f'"{package}"' not in optional_block
    for package in ("torch", "ultralytics", "onnx", "onnxruntime-gpu"):
        assert f'    "{package}",' not in optional_block
    assert "pyinstaller" not in build_script.lower()
    assert "iscc" not in build_script.lower()
    assert "src.devtools.model_export_package" in build_script
    assert "YOLOTool_ExtraEnv_${Version}.7z" in build_script
    assert "FILTER_LZMA2" in collector
    assert "PRESET_EXTREME" in collector
    assert not Path("installer/model_export_runtime.iss").exists()


def test_base_runtime_bundles_native_7zip_for_fast_extension_install():
    spec = Path("installer/YOLOTool.spec").read_text(encoding="utf-8")

    assert 'native_7z = shutil.which("7z.exe") or shutil.which("7z")' in spec
    assert 'datas += [(native_7z, ".")]' in spec
    assert 'native_7z_dll = str(Path(native_7z).with_name("7z.dll"))' in spec
