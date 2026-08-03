from pathlib import Path


def test_model_export_dependencies_are_split_between_pixi_environments():
    manifest = Path("pixi.toml").read_text(encoding="utf-8")
    assert "[feature.release-base.pypi-dependencies]" not in manifest
    assert "[feature.export-full.pypi-dependencies]" not in manifest
    gpu_block = manifest.split("[feature.release-gpu.pypi-dependencies]", 1)[1].split(
        "[environments]", 1
    )[0]
    cpu_block = manifest.split("[feature.release-cpu.pypi-dependencies]", 1)[1].split(
        "[feature.release-gpu.pypi-dependencies]", 1
    )[0]
    common_block = manifest.split("[pypi-dependencies]", 1)[1].split(
        "[feature.cpu.pypi-dependencies]", 1
    )[0]

    assert "[feature.release-gpu.pypi-dependencies]" in manifest
    assert "onnxruntime-gpu =" in gpu_block
    assert "onnxruntime =" not in gpu_block
    assert "onnxruntime =" in cpu_block
    assert "onnxruntime-gpu =" not in cpu_block
    assert "[feature.cpu.pypi-dependencies]" in manifest
    assert 'torch = { version = "*", index = "https://download.pytorch.org/whl/cpu" }' in manifest
    assert "[feature.release-cpu.pypi-dependencies]" in manifest
    assert 'sam2 = { path = "installer/vendor/sam2-1.1.0-cp312-cp312-win_amd64.whl" }' in manifest
    assert 'onnxscript = ">=0.7.1, <0.8"' in manifest
    assert 'nncf = ">=2.14.0, <3"' in common_block
    assert "nncf =" not in cpu_block
    assert "nncf =" not in gpu_block
    for package in ("openvino", "openvino-telemetry", "ncnn", "pnnx"):
        assert f"{package} =" in cpu_block
        assert f"{package} =" in gpu_block
    assert "tensorrt-cu13-libs" in manifest
    assert 'py7zr = ' in manifest
    environments_block = manifest.split("[environments]", 1)[1]
    assert 'default = ["gpu", "release-gpu"]' in environments_block
    assert 'release-gpu = ["gpu", "release-gpu"]' not in environments_block
    assert 'release-cpu = ["cpu", "release-cpu"]' in environments_block


def test_model_export_runtime_build_contract_is_present():
    base_spec = Path("installer/YOLOTool.spec").read_text(encoding="utf-8")
    build_script = Path("installer/build_model_export_runtime.ps1").read_text(encoding="utf-8")
    collector = Path("src/devtools/model_export_package.py").read_text(encoding="utf-8")
    boundaries = Path("src/devtools/runtime_package_boundaries.py").read_text(
        encoding="utf-8"
    )

    assert "BASE_EXPORT_PACKAGES" not in base_spec
    assert 'SAM2_PACKAGES = ("sam2",)' in base_spec
    optional_block = boundaries.split("GPU_EXTRA_DISTRIBUTIONS", 1)[1].split(")", 1)[0]
    for package in (
        "openvino",
        "openvino-telemetry",
        "nncf",
        "networkx",
        "scipy",
        "pandas",
        "ncnn",
        "pnnx",
        "tensorrt",
    ):
        assert f'"{package}"' in optional_block
    for package in ("tqdm", "portalocker"):
        assert f'"{package}"' not in optional_block
    for package in ("torch", "ultralytics", "onnx", "onnxscript", "onnx_ir", "onnxruntime-gpu"):
        assert f'    "{package}",' not in optional_block
    assert "pyinstaller" not in build_script.lower()
    assert "iscc" not in build_script.lower()
    assert "src.devtools.model_export_package" in build_script
    assert "pixi run -e default python" in build_script
    assert "YOLOTool_ExtraEnv_${Version}.7z" in build_script
    assert "SplitArchive" in build_script
    assert "GPU_EXTRA_DISTRIBUTIONS" in collector
    assert "collect_runtime_overlays" in collector
    assert "ORT_GPU_OVERLAY_DIR" in collector
    assert 'shutil.which("7z") or shutil.which("7z.exe")' in collector
    assert '"-m0=lzma2"' in collector
    assert '"-mmt=on"' in collector
    assert '"--split"' in collector
    assert '"-v{EXTRA_ARCHIVE_VOLUME_BYTES}b"' in collector
    assert "--base-staging" in collector
    assert not Path("installer/model_export_runtime.iss").exists()


def test_runtime_package_boundaries_are_shared_between_base_and_extra_builders():
    boundaries = Path("src/devtools/runtime_package_boundaries.py").read_text(
        encoding="utf-8"
    )
    base_builder = Path("src/devtools/base_runtime_builder.py").read_text(
        encoding="utf-8"
    )
    collector = Path("src/devtools/model_export_package.py").read_text(
        encoding="utf-8"
    )

    for package in (
        "openvino",
        "openvino-telemetry",
        "nncf",
        "networkx",
        "scipy",
        "pandas",
        "ncnn",
        "pnnx",
        "tensorrt",
    ):
        assert f'"{package}"' in boundaries
    assert "extension_distribution_paths" in base_builder
    assert "exclude_roots=extension_roots" in base_builder
    assert "_validate_no_base_overlap" in collector
    assert "GPU_BASE_EXCLUDED_DISTRIBUTIONS" in boundaries
    assert '"onnxruntime-gpu"' in boundaries


def test_extension_manifest_supports_optional_openvino_and_ncnn_formats():
    collector = Path("src/devtools/model_export_package.py").read_text(encoding="utf-8")

    assert '"supported_formats": ["openvino", "engine", "ncnn"]' in collector
    assert '"runtime_overlays": {ORT_GPU_OVERLAY_KEY: ORT_GPU_OVERLAY_DIR}' in collector
    assert "file_hashes" not in collector


def test_base_runtime_bundles_native_7zip_for_fast_extension_install():
    spec = Path("installer/YOLOTool.spec").read_text(encoding="utf-8")

    assert 'native_7z = shutil.which("7z.exe") or shutil.which("7z")' in spec
    assert 'datas += [(native_7z, ".")]' in spec
    assert 'native_7z_dll = str(Path(native_7z).with_name("7z.dll"))' in spec
