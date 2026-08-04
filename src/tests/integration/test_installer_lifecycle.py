from __future__ import annotations

from pathlib import Path


INSTALLER = Path("installer/yolo_tool.iss")


def _section(source: str, start: str, end: str) -> str:
    return source.split(start, 1)[1].split(end, 1)[0]

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
