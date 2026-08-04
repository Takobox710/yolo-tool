from __future__ import annotations

from pathlib import Path


INSTALLER = Path("installer/yolo_tool.iss")


def _section(source: str, start: str, end: str) -> str:
    return source.split(start, 1)[1].split(end, 1)[0]

def test_program_update_build_uses_program_only_output_without_runtime_layer():
    package_script = Path("installer/package_windows.ps1").read_text(encoding="utf-8")
    build_script = Path("installer/build_windows.ps1").read_text(encoding="utf-8")

    assert "-ProgramOnly:$ProgramOnly" in package_script
    assert "Get-ChildItem -LiteralPath $BuildPath -Filter $ExeName -File -Recurse" in build_script
    assert 'Remove-Item -LiteralPath $AppDir -Recurse -Force' in build_script
    assert '仅程序输出异常包含 _internal' in build_script
    assert '"sam2.1_hiera_base_plus.pt"' in build_script

def test_program_only_excludes_external_runtime_python_layers():
    spec = Path("installer/YOLOTool.spec").read_text(encoding="utf-8")
    boundaries = Path("src/devtools/runtime_package_boundaries.py").read_text(
        encoding="utf-8"
    )

    assert "PROGRAM_EXTERNAL_RUNTIME_EXCLUDES" in spec
    assert "*PROGRAM_EXTERNAL_RUNTIME_EXCLUDES" in spec
    assert "if str(ROOT) not in sys.path" in spec
    for package in (
        "numpy",
        "scipy",
        "pandas",
        "networkx",
        "torchvision",
        "sam2",
        "sam3",
        "timm",
        "huggingface_hub",
        "fsspec",
        "einops",
        "iopath",
        "pycocotools",
        "hydra",
        "omegaconf",
        "antlr4",
        "typing_extensions",
    ):
        assert f'    "{package}",' in boundaries

def test_packaging_menu_splats_named_arguments_for_child_scripts():
    menu_script = Path("installer/packaging_menu.ps1").read_text(encoding="utf-8")

    assert "$NamedArguments = @{}" in menu_script
    assert "$NamedArguments[$Name] = $true" in menu_script
    assert "& $scriptPath @NamedArguments" in menu_script

def test_model_export_archive_builder_supports_checked_split_volumes():
    builder = Path("src/devtools/model_export_package.py").read_text(encoding="utf-8")
    archive = Path("src/devtools/archive_builder.py").read_text(encoding="utf-8")
    script = Path("installer/build_model_export_runtime.ps1").read_text(encoding="utf-8")

    assert "EXTRA_ARCHIVE_VOLUME_BYTES = 1_073_700_000" in builder
    assert "EXTRA_ARCHIVE_VOLUME_COUNT = 2" in builder
    assert "MAX_ARCHIVE_VOLUME_BYTES = 1_073_741_824" in builder
    assert 'command.append(f"-v{volume_bytes}b")' in archive
    assert "归档分卷必须严格小于 1 GiB" in archive
    assert 'parser.add_argument("--split", action="store_true")' in builder
    assert '[switch]$SplitArchive' in script
    assert '"--split"' in script
    assert '[regex]::Escape("YOLOTool_ExtraEnv_${Version}.7z")' in script

def test_archive_builders_preserve_the_alternate_archive_format():
    base_script = Path("installer/build_base_runtime_models.ps1").read_text(encoding="utf-8")
    extra_script = Path("installer/build_model_export_runtime.ps1").read_text(encoding="utf-8")
    base_builder = Path("src/devtools/base_runtime_builder.py").read_text(encoding="utf-8")
    extra_builder = Path("src/devtools/model_export_package.py").read_text(encoding="utf-8")
    archive_builder = Path("src/devtools/archive_builder.py").read_text(encoding="utf-8")

    assert 'if ($SplitBaseArchive)' in base_script
    assert 'if ($SplitArchive)' in extra_script
    assert 'Where-Object { $_.Name -match $VolumePattern }' in base_script
    assert 'Where-Object { $_.Name -match $VolumePattern }' in extra_script
    assert '[0-9]{{3}}' in base_script
    assert '[0-9]{{3}}' in extra_script
    assert 'if split:' in archive_builder
    assert 'archive_path.unlink(missing_ok=True)' in archive_builder
    assert 'split=split' in base_builder
    assert 'split=split' in extra_builder

def test_gpu_full_packaging_rebuilds_program_only_installer_after_base_runtime():
    package_script = Path("installer/package_windows.ps1").read_text(encoding="utf-8")

    assert 'if ($BuildBaseRuntimeModels -and -not $IntegratedRuntime)' in package_script
    assert "-Mode release -Clean:$Clean -PackageType Program `" in package_script
    assert "ProgramOnly:$ProgramOnly" in package_script
    assert 'Join-Path $ProgramStaging "_internal"' in package_script
    assert "拒绝生成重复携带运行环境的安装器" in package_script

def test_full_frozen_build_writes_standalone_runtime_manifests():
    build_script = Path("installer/build_windows.ps1").read_text(encoding="utf-8")

    assert "if (-not $ProgramOnly)" in build_script
    assert 'Join-Path $AppDir "release-manifest.json"' in build_script
    assert 'Join-Path $AppDir "runtime-manifest.json"' in build_script
    assert "UTF8Encoding]::new($false)" in build_script
    assert "files = @{}" in build_script

def test_full_packaging_always_builds_base_archive():
    package_script = Path("installer/package_windows.ps1").read_text(encoding="utf-8")
    base_script = Path("installer/build_base_runtime_models.ps1").read_text(encoding="utf-8")
    extension_script = Path("installer/build_model_export_runtime.ps1").read_text(
        encoding="utf-8"
    )

    assert "--check-current" not in package_script
    assert "$BaseArchiveCurrent" not in package_script
    assert "--check-current" not in base_script
    assert "cache.json" not in base_script
    assert "--force" not in extension_script

def test_full_packaging_reselects_base_archive_after_build():
    package_script = Path("installer/package_windows.ps1").read_text(encoding="utf-8")

    build_call = 'throw "Base runtime and models build failed with exit code $LASTEXITCODE"'
    build_index = package_script.index(build_call)
    resolve_index = package_script.index("$BaseArchive = if ($SplitBaseArchive)", build_index)

    assert resolve_index > build_index
    assert "$BaseArchiveFirstVolume" in package_script[resolve_index : resolve_index + 180]
    assert "$BaseArchivePath" in package_script[resolve_index : resolve_index + 180]

def test_program_only_spec_skips_external_runtime_analysis():
    spec = Path("installer/YOLOTool.spec").read_text(encoding="utf-8")

    assert "if is_program_only:" in spec
    assert "hook_paths = []" in spec
    assert '"ultralytics",' in spec
    assert '"torch",' in spec
    assert '"onnxruntime",' in spec
    assert "collect_submodules(\"ultralytics\"" in spec
    assert "pyi_rth_pyside6.py" in spec
    assert '"ctypes.util"' in spec
