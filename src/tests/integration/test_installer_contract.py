from __future__ import annotations

from pathlib import Path


INSTALLER = Path("installer/yolo_tool.iss")


def _section(source: str, start: str, end: str) -> str:
    return source.split(start, 1)[1].split(end, 1)[0]


def test_release_artifact_names_and_versions_are_short_and_stable():
    installer = INSTALLER.read_text(encoding="utf-8")
    package_script = Path("installer/package_windows.ps1").read_text(encoding="utf-8")
    base_builder = Path("src/devtools/release_package.py").read_text(encoding="utf-8")
    extra_builder = Path("src/devtools/model_export_package.py").read_text(
        encoding="utf-8"
    )

    assert "OutputBaseFilename={#MyAppName}_Setup_{#MyAppVersion}" in installer
    assert "YOLOTool_BaseEnv_${BaseVersion}.7z" in package_script
    assert "YOLOTool_ExtraEnv_${ExtensionVersion}.7z" in package_script
    assert "YOLOTool_BaseEnv_{package_version}.7z" in base_builder
    assert "YOLOTool_ExtraEnv_{version}.7z" in extra_builder
    assert Path("installer/base-runtime-models-version.txt").read_text().strip() == "v2"
    assert Path("installer/model-export-runtime-version.txt").read_text().strip() == "v2"
    assert Path("installer/runtime-version.txt").read_text().strip() == "runtime-2"


def test_base_runtime_uses_parallel_python_source_copy_with_fallback():
    source = Path("src/devtools/release_package.py").read_text(encoding="utf-8")

    assert 'shutil.which("robocopy") if os.name == "nt" else None' in source
    assert '"/MT:16"' in source
    assert '"*.py"' in source
    assert '"/XD"' in source
    assert "for source in sorted(site_packages.rglob(\"*.py\"))" in source


def test_component_page_uses_fast_candidate_checks_and_defers_hashing():
    source = INSTALLER.read_text(encoding="utf-8")
    refresh = _section(source, "procedure RefreshComponentPage();", "procedure BrowseBaseClick")
    prepare = _section(source, "function PrepareToInstall", "procedure CurStepChanged")

    assert "GetSHA256OfFile" not in refresh
    assert "FileSize64(FileName, ActualSize)" in source
    assert "BaseCompressedSize" in source
    assert "ExtensionCompressedSize" in source
    assert "VerifyArchiveHash(BaseArchivePath" in prepare
    assert "VerifyArchiveHash(ExtensionArchivePath" in prepare
    assert "BeginArchiveVerification('正在验证本体环境包，请稍候...');" in prepare
    assert "ProgressGauge.Style := npbstMarquee" in source


def test_installer_warns_for_missing_base_without_blocking_and_cleans_up_on_finish():
    source = INSTALLER.read_text(encoding="utf-8")

    assert '#define GitHubReleaseUrl "https://github.com/Takobox710/yolo-tool/releases"' in source
    assert "BaseGithubButton: TNewButton" in source
    assert "BaseGithubButton.Visible := BaseIsRequired and not IsValidBaseArchive();" in source
    assert "未找到匹配基础环境包，将继续使用旧环境；可能导致部分功能缺失。" in source
    assert "当前安装必须提供匹配的本体环境和模型包。' + #13#10 +" not in source
    next_page = _section(source, "function NextButtonClick", "procedure BrowseBaseClick")
    assert "BaseIsRequired and not IsValidBaseArchive()" not in next_page
    assert "进入 GitHub 下载" in source
    assert "CleanupPackagesCheck: TNewCheckBox" in source
    assert "安装完成后删除本次使用的安装包和环境包" in source
    assert "CleanupInstallSources();" in source
    assert "ScheduleDeleteFile(ExpandConstant('{srcexe}'));" in source
    assert "ScheduleDeleteFile(BaseArchivePath);" in source
    assert "ScheduleDeleteFile(ExtensionArchivePath);" in source


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


def test_installer_uses_named_uninstaller_and_visible_verification_page():
    source = INSTALLER.read_text(encoding="utf-8")

    assert 'Type: files; Name: "{app}\\uninstall.exe"' in source
    assert 'Type: files; Name: "{app}\\uninstall.dat"' in source
    assert "VerificationPage: TOutputProgressWizardPage" in source
    assert "CreateOutputProgressPage('正在验证安装包'" in source
    assert "VerificationPage.Show" in source
    assert "VerificationPage.Hide" in source
    assert "Uninstaller := ExpandConstant('{app}\\uninstall.exe')" in source
    assert "RenameUninstallerFiles()" in source


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
    assert "ProgressGauge.Position := WizardForm.ProgressGauge.Max" in changed_step
