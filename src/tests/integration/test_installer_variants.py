from __future__ import annotations

from pathlib import Path


INSTALLER = Path("installer/yolo_tool.iss")


def _section(source: str, start: str, end: str) -> str:
    return source.split(start, 1)[1].split(end, 1)[0]

def test_cpu_variant_has_isolated_artifacts_and_runtime_selection():
    package_script = Path("installer/package_windows.ps1").read_text(encoding="utf-8")
    base_script = Path("installer/build_base_runtime_models.ps1").read_text(encoding="utf-8")
    build_script = Path("installer/build_windows.ps1").read_text(encoding="utf-8")
    installer = INSTALLER.read_text(encoding="utf-8")
    spec = Path("installer/YOLOTool.spec").read_text(encoding="utf-8")

    assert '[ValidateSet("GPU", "CPU")]' in package_script
    assert '"YOLOTool_CPU"' in package_script
    assert '"--variant", $Variant.ToLowerInvariant()' in build_script
    assert '"release-cpu"' in build_script
    assert '"default"' in build_script
    assert '"default"' in package_script
    assert '"default"' in base_script
    assert '"YOLOTool_CPU"' in base_script
    assert '[switch]$SplitBaseArchive' in base_script
    assert '"--split"' in base_script
    assert '${ArtifactPrefix}_BaseEnv_' in package_script
    assert 'BaseRuntimeModels-CPU' not in package_script
    assert '"sam2.1_hiera_tiny.pt"' in build_script
    assert 'CPU 一体式安装包缺少完整冻结目录' in package_script
    assert '"/DPackageVariant=$($Variant.ToLowerInvariant())"' in package_script
    assert '#define PackageVariant "gpu"' in installer
    assert '#define ArtifactPrefix "YOLOTool"' in installer
    assert 'build_variant = os.environ.get("YOLO_TOOL_BUILD_VARIANT", "gpu")' in spec
    assert 'runtime_distribution = "onnxruntime" if is_cpu_variant else "onnxruntime-gpu"' in spec
    assert 'runtime_distribution,' in spec
    assert 'runtime_packages += ["openvino", "ncnn", "pnnx", "nncf"]' in spec

def test_cpu_is_an_integrated_installer_and_gpu_keeps_external_archives():
    package_script = Path("installer/package_windows.ps1").read_text(encoding="utf-8")
    installer = INSTALLER.read_text(encoding="utf-8")
    catalog = Path("src/devtools/companion_catalog.py").read_text(encoding="utf-8")

    assert 'if ($IntegratedRuntime) {' in package_script
    assert '-NoArchive' in package_script
    assert 'dist\\CPU\\YOLOTool' in package_script
    assert '/DIntegratedRuntime=1' in package_script
    assert '/DIntegratedRuntimeDirect=1' in package_script
    assert '#ifdef IntegratedRuntime' in installer
    assert '..\\dist\\CPU\\YOLOTool\\*' in installer
    assert 'Excludes: "YOLOTool.exe"' in installer
    assert 'Source: "{code:GetBaseArchivePath}"' in installer
    assert 'integrated=True' in catalog

def test_cpu_update_and_packaging_menu_contract_hides_gpu_extra_environment():
    package_script = Path("installer/package_windows.ps1").read_text(encoding="utf-8")
    batch_script = Path("打包程序.bat").read_text(encoding="utf-8")
    menu_script = Path("installer/packaging_menu.ps1").read_text(encoding="utf-8")
    dialog_layout = Path(
        "src/ui/features/settings/update_dialog_layout.py"
    ).read_text(encoding="utf-8")
    dialog_state = Path(
        "src/ui/features/settings/update_dialog_state.py"
    ).read_text(encoding="utf-8")

    assert "CPU 版不支持构建模型转换附加环境" in package_script
    assert "packaging_menu.ps1" in batch_script
    assert "ReadKey" in menu_script
    assert "[Q] 退出" in menu_script
    assert '"-Clean", "-SplitArchive"' in menu_script
    assert '"-Variant", "GPU", "-Clean", "-SplitBaseArchive"' in menu_script
    assert "pwsh.exe -NoProfile" in batch_script
    assert not Path("打包更新程序.bat").exists()
    program_only_menu_item = menu_script.split('"7" {', 1)[1].split('"8" {', 1)[0]
    assert 'Invoke-PackagingScript "installer\\package_windows.ps1"' in program_only_menu_item
    assert "BuildBaseRuntimeModels" not in program_only_menu_item
    assert "BuildModelExportRuntime" not in program_only_menu_item
    assert "normalize_variant(dialog.result.variant) != CPU_VARIANT" in dialog_layout
    assert "normalize_variant(result.variant) != CPU_VARIANT" in dialog_state

def test_cpu_spec_filters_non_cpu_openvino_payloads():
    spec = Path("installer/YOLOTool.spec").read_text(encoding="utf-8")

    for filename in (
        "openvino_auto_batch_plugin.dll",
        "openvino_auto_plugin.dll",
        "openvino_hetero_plugin.dll",
        "openvino_intel_gpu_plugin.dll",
        "openvino_intel_npu_compiler.dll",
        "openvino_intel_npu_compiler_loader.dll",
        "openvino_intel_npu_plugin.dll",
        "cache.json",
    ):
        assert f'"{filename}"' in spec
    assert 'name.endswith((".lib", "_debug.lib"))' in spec
    assert "_collect_cpu_openvino_files" in spec

def test_sam3_vendor_runtime_is_packaged_without_checkpoint():
    spec = Path("installer/YOLOTool.spec").read_text(encoding="utf-8")
    pixi = Path("pixi.toml").read_text(encoding="utf-8")
    build_script = Path("installer/build_windows.ps1").read_text(encoding="utf-8")
    wheel = Path("installer/vendor/sam3-0.1.0-py3-none-any.whl")
    license_file = Path("installer/vendor/sam3-LICENSE.txt")

    assert 'SAM3_PACKAGES = ("sam3",)' in spec
    assert '*SAM3_PACKAGES' in spec
    assert 'sam3 = { path = "installer/vendor/sam3-0.1.0-py3-none-any.whl" }' in pixi
    assert wheel.is_file() and wheel.stat().st_size > 0
    assert license_file.is_file() and "SAM License" in license_file.read_text(encoding="utf-8")
    assert "sam3.pt" not in build_script

def test_sam3_runtime_dependency_contract_excludes_training_accelerators():
    import zipfile

    pixi = Path("pixi.toml").read_text(encoding="utf-8")
    with zipfile.ZipFile("installer/vendor/sam3-0.1.0-py3-none-any.whl") as archive:
        metadata_name = next(name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))
        metadata = archive.read(metadata_name).decode("utf-8")

    for dependency in ("timm", "ftfy", "iopath", "huggingface-hub", "einops", "pycocotools"):
        assert dependency in pixi
    assert "Requires-Dist: numpy<3" in metadata
    assert "Requires-Dist: flash-attn" not in metadata
    assert "Requires-Dist: triton" not in metadata

def test_model_export_extension_lives_inside_internal_and_survives_base_replacement():
    source = INSTALLER.read_text(encoding="utf-8")

    assert "Result := ExpandConstant('{app}\\_internal\\extensions');" in source
    assert "function PreserveExtensionForBaseInstall" in source
    assert "function RestorePreservedExtension" in source
    assert "PreserveExtensionForBaseInstall() and" in source
    assert "MoveStaged(BaseStagePath('_internal'), '_internal') and" in source
    assert "RestorePreservedExtension();" in source
