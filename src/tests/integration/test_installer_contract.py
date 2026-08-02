from __future__ import annotations

from pathlib import Path


INSTALLER = Path("installer/yolo_tool.iss")


def _section(source: str, start: str, end: str) -> str:
    return source.split(start, 1)[1].split(end, 1)[0]


def test_release_artifact_names_and_versions_are_short_and_stable():
    installer = INSTALLER.read_text(encoding="utf-8")
    package_script = Path("installer/package_windows.ps1").read_text(encoding="utf-8")
    base_builder = Path("src/devtools/base_runtime_builder.py").read_text(encoding="utf-8")
    extra_builder = Path("src/devtools/model_export_package.py").read_text(
        encoding="utf-8"
    )

    assert "OutputBaseFilename={#ArtifactPrefix}_Setup_{#MyAppVersion}" in installer
    assert "${ArtifactPrefix}_BaseEnv_${BaseVersion}.7z" in package_script
    assert "-SplitBaseArchive:$SplitBaseArchive" in package_script
    assert "-NoArchive" in package_script
    assert "YOLOTool_ExtraEnv_${ExtensionVersion}.7z" in package_script
    assert "_BaseEnv_{package_version}.7z" in base_builder
    assert "-v{BASE_ARCHIVE_VOLUME_BYTES}b" in base_builder
    assert "YOLOTool_ExtraEnv_{version}.7z" in extra_builder
    assert Path("installer/base-runtime-models-version.txt").read_text().strip() == "v3"
    assert Path("installer/model-export-runtime-version.txt").read_text().strip() == "v3"
    assert Path("installer/runtime-version.txt").read_text().strip() == "runtime-2"


def test_inno_setup_7_compiler_is_required():
    package_script = Path("installer/package_windows.ps1").read_text(encoding="utf-8")

    assert '"Inno Setup 7\\ISCC.exe"' in package_script
    assert 'DisplayName -match "^Inno Setup(?: version)?\\s+7' in package_script
    assert "Inno Setup 7 Command-Line Compiler" in package_script
    assert "Install Inno Setup 7.0.2 or newer." in package_script


def test_cpu_installer_uses_short_cpu_shortcut_name():
    installer = INSTALLER.read_text(encoding="utf-8")
    package_script = Path("installer/package_windows.ps1").read_text(encoding="utf-8")

    assert '#ifndef ShortcutName' in installer
    assert "if '{#ShortcutName}' <> '' then" in installer
    assert '"/DShortcutName=YOLOTool_CPU"' in package_script


def test_base_runtime_uses_parallel_python_source_copy_with_fallback():
    source = Path("src/devtools/release_package.py").read_text(encoding="utf-8")

    assert 'shutil.which("robocopy") if os.name == "nt" else None' in source
    assert '"/MT:16"' in source
    assert '"*.py"' in source
    assert '"/XD"' in source
    assert "for source in sorted(site_packages.rglob(\"*.py\"))" in source


def test_component_page_uses_environment_version_without_archive_hashing():
    source = INSTALLER.read_text(encoding="utf-8")
    prepare = _section(source, "function PrepareToInstall", "procedure CurStepChanged")

    assert "GetSHA256OfFile" not in source
    assert "FileSize64(FileName, ActualSize)" not in source
    assert "IsVersionedArchiveCandidate(BaseArchivePath" in source
    assert "ArchiveExtraction=full" in source
    assert "CompareText(ExtractFileExt(FileName), '.7z') = 0" in source
    assert "ChangeFileExt(FileName, '.003')" in source
    assert "IsVersionedArchiveCandidate(ExtensionArchivePath" in source
    assert "BaseCompressedSize" not in source
    assert "ExtensionCompressedSize" not in source
    assert "VerifyArchiveHash" not in prepare


def test_installer_requires_base_for_first_install_and_cleans_up_on_finish():
    source = INSTALLER.read_text(encoding="utf-8")

    assert '#define GitHubReleaseUrl "https://github.com/Takobox710/yolo-tool/releases"' in source
    assert "BaseGithubButton: TNewButton" in source
    assert "BaseGithubButton.Visible := BaseIsRequired and not IsValidBaseArchive();" in source
    assert "首次安装必须提供匹配的基础环境和模型包，当前无法继续。" in source
    assert "未找到基础环境包，将仅安装程序；启动后可能缺少运行环境。" not in source
    next_page = _section(source, "function NextButtonClick", "procedure BrowseBaseClick")
    assert "if (not ExistingInstall) and BaseIsRequired and" in next_page
    assert "首次安装必须提供匹配的本体环境和模型包。' + #13#10 +" in next_page
    assert "未找到匹配基础环境包，将继续使用旧环境；可能导致部分功能缺失。" in source
    assert "进入 GitHub 下载" in source
    assert "安装完成后删除本次使用的安装包和环境包" in source
    assert 'Filename: "{cmd}"; Parameters: "{code:GetCleanupParameters}";' in source
    assert 'Flags: runhidden postinstall unchecked skipifsilent; Check: MainInstallSucceeded' in source
    assert "function GetCleanupParameters(Param: String): String;" in source
    assert "ExpandConstant('{srcexe}')" in source
    assert "Result := Result + ' & del /f /q \"' + BaseArchivePath + '\"';" in source
    assert "ChangeFileExt(BaseArchivePath, '.002')" in source
    assert "Result := Result + ' & del /f /q \"' + ExtensionArchivePath + '\"';" in source
    assert "CleanupPackagesCheck" not in source
    assert "CleanupPackagesStatus" not in source
    assert "function ShouldInstallBase(): Boolean; forward;" in source


def test_gui_startup_does_not_block_on_runtime_version_mismatch():
    source = Path("src/ui/app.py").read_text(encoding="utf-8")

    assert "check_runtime_compatibility" not in source
    assert "运行环境不兼容" not in source


def test_installer_has_nonblocking_directory_and_safe_cancel_contract():
    source = INSTALLER.read_text(encoding="utf-8")
    deinitialize = _section(source, "procedure DeinitializeSetup();", "function InitializeUninstall")

    assert "DirExistsWarning=no" in source
    assert "DirectoryHasEntries" not in source
    assert "TransactionInitialized and not UpdateCommitted" in deinitialize
    assert "ExpandConstant('{app}')" not in deinitialize
    assert "TransactionAppDir" in source


def test_installer_uses_named_uninstaller_without_archive_verification_page():
    source = INSTALLER.read_text(encoding="utf-8")

    assert 'Type: files; Name: "{app}\\uninstall.exe"' in source
    assert 'Type: files; Name: "{app}\\uninstall.dat"' in source
    assert "VerificationPage: TOutputProgressWizardPage" not in source
    assert "Uninstaller := ExpandConstant('{app}\\uninstall.exe')" in source
    assert "RenameUninstallerFiles()" in source


def test_installer_uses_restart_manager_for_the_target_instance():
    source = INSTALLER.read_text(encoding="utf-8")

    assert "CloseApplications=force" in source
    assert "CloseApplicationsFilter=YOLOTool.exe" in source
    assert "RestartApplications=no" in source
    assert "procedure RegisterExtraCloseApplicationsResources()" in source
    assert "RegisterExtraCloseApplicationsResource(" in source
    assert "ExpandConstant('{app}\\{#MyAppExeName}'));" in source
    assert "powershell.exe" not in source
    assert "Get-CimInstance" not in source
    assert "Stop-Process" not in source
    prepare = _section(source, "function PrepareToInstall", "procedure CurStepChanged")
    assert "StopRunningTargetProcess()" not in prepare


def test_installed_metadata_and_root_model_are_managed_by_installer():
    source = INSTALLER.read_text(encoding="utf-8")

    assert '#define MetadataRelativeRoot "_internal\\yolotool_metadata"' in source
    for filename in (
        "app-version.txt",
        "release-manifest.json",
        "runtime-manifest.json",
        "base-package-manifest.json",
        "managed-models.json",
        "package-info.ini",
        "install-instance.ini",
    ):
        assert f"MetadataRelativePath('{filename}')" in source or (
            f"InstalledMetadataPath('{filename}')" in source
        )
    assert "BaseStagePath('data\\models\\yolo26n.pt')" in source
    assert 'Type: files; Name: "{app}\\yolo26n.pt"' in source
    assert "BackupExisting('runtime-version.txt')" in source


def test_model_export_extension_lives_inside_internal_and_survives_base_replacement():
    source = INSTALLER.read_text(encoding="utf-8")

    assert "Result := ExpandConstant('{app}\\_internal\\extensions');" in source
    assert "function PreserveExtensionForBaseInstall" in source
    assert "function RestorePreservedExtension" in source
    assert "PreserveExtensionForBaseInstall() and" in source
    assert "MoveStaged(BaseStagePath('_internal'), '_internal') and" in source
    assert "RestorePreservedExtension();" in source


def test_program_update_build_uses_program_only_output_without_runtime_layer():
    package_script = Path("installer/package_windows.ps1").read_text(encoding="utf-8")
    build_script = Path("installer/build_windows.ps1").read_text(encoding="utf-8")

    assert "-ProgramOnly:$ProgramOnly" in package_script
    assert "Get-ChildItem -LiteralPath $BuildPath -Filter $ExeName -File -Recurse" in build_script
    assert 'Remove-Item -LiteralPath $AppDir -Recurse -Force' in build_script
    assert '仅程序输出异常包含 _internal' in build_script
    assert '"sam2.1_hiera_base_plus.pt"' in build_script


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
    assert '"release-gpu"' in build_script
    assert '"release-gpu"' in package_script
    assert '"release-gpu"' in base_script
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


def test_cpu_update_and_batch_contract_hides_gpu_extra_environment():
    package_script = Path("installer/package_windows.ps1").read_text(encoding="utf-8")
    batch_script = Path("打包程序.bat").read_text(encoding="utf-8")
    menu_script = Path("installer/packaging_menu.ps1").read_text(encoding="utf-8")
    update_batch = Path("打包更新程序.bat").read_text(encoding="utf-8")
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
    assert "pwsh.exe -NoProfile" in update_batch
    assert "normalize_variant(dialog.result.variant) != CPU_VARIANT" in dialog_layout
    assert "normalize_variant(result.variant) != CPU_VARIANT" in dialog_state


def test_packaging_menu_splats_named_arguments_for_child_scripts():
    menu_script = Path("installer/packaging_menu.ps1").read_text(encoding="utf-8")

    assert "$NamedArguments = @{}" in menu_script
    assert "$NamedArguments[$Name] = $true" in menu_script
    assert "& $scriptPath @NamedArguments" in menu_script


def test_model_export_archive_builder_supports_checked_split_volumes():
    builder = Path("src/devtools/model_export_package.py").read_text(encoding="utf-8")
    script = Path("installer/build_model_export_runtime.ps1").read_text(encoding="utf-8")

    assert "EXTRA_ARCHIVE_VOLUME_BYTES = 1_073_700_000" in builder
    assert "EXTRA_ARCHIVE_VOLUME_COUNT = 2" in builder
    assert "MAX_ARCHIVE_VOLUME_BYTES = 1_073_741_824" in builder
    assert 'command.append(f"-v{EXTRA_ARCHIVE_VOLUME_BYTES}b")' in builder
    assert "附加环境包分卷必须严格小于 1 GiB" in builder
    assert 'parser.add_argument("--split", action="store_true")' in builder
    assert '[switch]$SplitArchive' in script
    assert '"--split"' in script
    assert 'YOLOTool_ExtraEnv_${Version}.7z.???' in script


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


def test_base_archive_extraction_keeps_normal_install_progress():
    source = INSTALLER.read_text(encoding="utf-8")

    changed_step = _section(source, "procedure CurStepChanged", "procedure DeinitializeSetup")
    assert "CurStep = ssInstall" not in changed_step
    assert "ProgressGauge.Style := npbstMarquee" not in changed_step
    assert "ProgressGauge.Style := npbstNormal" in changed_step


def test_post_install_commit_keeps_progress_visible():
    source = INSTALLER.read_text(encoding="utf-8")
    changed_step = _section(source, "procedure CurStepChanged", "procedure DeinitializeSetup")

    assert "正在完成安装，请稍候..." in changed_step
    assert "if ShouldInstallBase() then" in changed_step
    assert "已保留当前运行环境，跳过环境版本自检。" in changed_step
    assert "警告：当前基础环境与新程序不匹配或不完整。" in changed_step
    assert "本次将继续使用旧环境，部分功能可能无法使用。" in changed_step
    assert "警告：新程序运行环境版本不一致或自检未通过。" in changed_step
    assert "安装将继续，但部分功能可能无法使用。" in changed_step
    assert "新程序运行环境自检失败，正在恢复旧版本。" not in changed_step
    assert changed_step.count("RestoreMainInstall();") == 3
    assert "ProgressGauge.Position := WizardForm.ProgressGauge.Max" in changed_step
