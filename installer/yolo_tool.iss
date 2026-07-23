#ifndef MyAppVersion
#define MyAppVersion "1.2.7"
#endif
#ifndef PackageType
#define PackageType "Full"
#endif
#ifndef RequiredRuntimeVersion
#define RequiredRuntimeVersion ""
#endif
#define MyAppName "YOLOTool"
#define MyAppPublisher "Takobox"
#define MyAppExeName "YOLOTool.exe"
#define MyAppIdEscaped "{{AFD7B4C3-5B11-4F8D-8BA1-64D96FD3C4A1}"
#define MyAppIdValue "{AFD7B4C3-5B11-4F8D-8BA1-64D96FD3C4A1}"

#if PackageType == "Full"
#define PackageLabel "Setup"
#else
#define PackageLabel PackageType
#endif

[Setup]
AppId={#MyAppIdEscaped}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
#if PackageType == "Full"
DefaultDirName={autopf}\{#MyAppName}
DisableDirPage=no
Uninstallable=yes
CreateUninstallRegKey=yes
#else
DefaultDirName={code:GetPreviousAppDir}
DisableDirPage=yes
Uninstallable=no
CreateUninstallRegKey=no
#endif
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=output
OutputBaseFilename={#MyAppName}_{#PackageLabel}_{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
CloseApplications=yes
RestartApplications=no
SetupIconFile=..\src\assets\app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

#if PackageType == "Full"
[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务:"; Flags: unchecked

[Dirs]
Name: "{app}\data\models"
Name: "{app}\data\runtime"
Name: "{app}\images"
Name: "{app}\labels"
Name: "{app}\result"
#endif

[Files]
#if PackageType == "Full" || PackageType == "AppUpdate" || PackageType == "RuntimeFull"
#if PackageType == "Full"
Source: "..\dist\packages\{#PackageType}\YOLOTool.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\packages\{#PackageType}\app_assets\*"; DestDir: "{app}\app_assets"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "..\dist\packages\{#PackageType}\app-version.txt"; DestDir: "{app}"; Flags: ignoreversion
#else
Source: "..\dist\packages\{#PackageType}\YOLOTool.exe"; DestDir: "{app}\.update-working"; Flags: ignoreversion
Source: "..\dist\packages\{#PackageType}\app_assets\*"; DestDir: "{app}\.update-working\app_assets"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "..\dist\packages\{#PackageType}\app-version.txt"; DestDir: "{app}\.update-working"; Flags: ignoreversion
#endif
#endif

#if PackageType == "Full" || PackageType == "RuntimeFull"
#if PackageType == "Full"
Source: "..\dist\packages\{#PackageType}\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
#else
Source: "..\dist\packages\{#PackageType}\_internal\*"; DestDir: "{app}\.update-working\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
#endif
#endif

#if PackageType == "Full"
Source: "..\dist\packages\{#PackageType}\data\models\*"; DestDir: "{app}\data\models"; Flags: ignoreversion skipifsourcedoesntexist recursesubdirs createallsubdirs
Source: "..\dist\packages\{#PackageType}\images\*"; DestDir: "{app}\images"; Flags: ignoreversion skipifsourcedoesntexist recursesubdirs createallsubdirs
Source: "..\dist\packages\{#PackageType}\labels\*"; DestDir: "{app}\labels"; Flags: ignoreversion skipifsourcedoesntexist recursesubdirs createallsubdirs
Source: "..\dist\packages\{#PackageType}\data\runtime\settings.json"; DestDir: "{app}\data\runtime"; Flags: onlyifdoesntexist
Source: "..\dist\packages\{#PackageType}\data\runtime\app_state.json"; DestDir: "{app}\data\runtime"; Flags: onlyifdoesntexist
Source: "..\dist\packages\{#PackageType}\result\*"; DestDir: "{app}\result"; Flags: onlyifdoesntexist skipifsourcedoesntexist recursesubdirs createallsubdirs
#endif

#if PackageType == "Full"
Source: "..\dist\packages\{#PackageType}\release-manifest.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\packages\{#PackageType}\runtime-manifest.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\packages\{#PackageType}\runtime-version.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\packages\{#PackageType}\package-info.ini"; DestDir: "{app}"; Flags: ignoreversion
#else
Source: "..\dist\packages\{#PackageType}\release-manifest.json"; DestDir: "{app}\.update-working"; Flags: ignoreversion
Source: "..\dist\packages\{#PackageType}\runtime-manifest.json"; DestDir: "{app}\.update-working"; Flags: ignoreversion
Source: "..\dist\packages\{#PackageType}\runtime-version.txt"; DestDir: "{app}\.update-working"; Flags: ignoreversion
Source: "..\dist\packages\{#PackageType}\package-info.ini"; DestDir: "{app}\.update-working"; Flags: ignoreversion
#endif

#if PackageType == "Full"
[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent
#endif

[Code]
var
  UpdateCommitStarted: Boolean;
  UpdateCommitted: Boolean;

function TryGetPreviousInstallDir(var InstallDir: String): Boolean;
var
  UninstallKey: String;
begin
  UninstallKey := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppIdValue}_is1';
  Result :=
    RegQueryStringValue(HKLM64, UninstallKey, 'InstallLocation', InstallDir) or
    RegQueryStringValue(HKLM32, UninstallKey, 'InstallLocation', InstallDir) or
    RegQueryStringValue(HKCU64, UninstallKey, 'InstallLocation', InstallDir) or
    RegQueryStringValue(HKCU32, UninstallKey, 'InstallLocation', InstallDir);
end;

function PreviousInstallExists(): Boolean;
var
  InstallDir: String;
begin
  Result := TryGetPreviousInstallDir(InstallDir);
end;

function GetPreviousAppDir(Param: String): String;
begin
  if not TryGetPreviousInstallDir(Result) then
    Result := ExpandConstant('{autopf}\{#MyAppName}');
end;

function ReadInstalledRuntimeVersion(): String;
begin
  Result := GetIniString('Package', 'runtime_version', '',
    ExpandConstant('{app}\package-info.ini'));
end;

function RunHiddenCommand(const CommandLine: String; var ExitCode: Integer): Boolean;
begin
  Result := Exec(ExpandConstant('{sys}\cmd.exe'), '/C ' + CommandLine,
    '', SW_HIDE, ewWaitUntilTerminated, ExitCode);
end;

function StagePath(const RelativePath: String): String;
begin
  Result := ExpandConstant('{app}\.update-working\' + RelativePath);
end;

function BackupPath(const RelativePath: String): String;
begin
  Result := ExpandConstant('{app}\.update-backup\' + RelativePath);
end;

function BackupExisting(const RelativePath: String): Boolean;
var
  SourcePath: String;
  DestinationPath: String;
begin
  SourcePath := ExpandConstant('{app}\' + RelativePath);
  DestinationPath := BackupPath(RelativePath);
  if FileExists(SourcePath) then
  begin
    ForceDirectories(ExtractFileDir(DestinationPath));
    Result := RenameFile(SourcePath, DestinationPath);
  end
  else if DirExists(SourcePath) then
  begin
    ForceDirectories(ExtractFileDir(DestinationPath));
    Result := RenameFile(SourcePath, DestinationPath);
  end
  else
    Result := True;
end;

function MoveStaged(const RelativePath: String): Boolean;
var
  SourcePath: String;
  DestinationPath: String;
begin
  SourcePath := StagePath(RelativePath);
  DestinationPath := ExpandConstant('{app}\' + RelativePath);
  ForceDirectories(ExtractFileDir(DestinationPath));
  Result := RenameFile(SourcePath, DestinationPath);
end;

function RemovePath(const RelativePath: String): Boolean;
var
  Path: String;
  ExitCode: Integer;
begin
  Path := ExpandConstant('{app}\' + RelativePath);
  if FileExists(Path) then
    Result := DeleteFile(Path)
  else if DirExists(Path) then
    Result := RunHiddenCommand('rmdir /S /Q "' + Path + '"', ExitCode) and (ExitCode = 0)
  else
    Result := True;
end;

function RestoreExisting(const RelativePath: String): Boolean;
var
  SourcePath: String;
  DestinationPath: String;
begin
  SourcePath := BackupPath(RelativePath);
  DestinationPath := ExpandConstant('{app}\' + RelativePath);
  if not (FileExists(SourcePath) or DirExists(SourcePath)) then
  begin
    Result := True;
    exit;
  end;
  RemovePath(RelativePath);
  ForceDirectories(ExtractFileDir(DestinationPath));
  Result := RenameFile(SourcePath, DestinationPath);
end;

function CommitUpdate(): Boolean;
begin
  UpdateCommitStarted := True;
  Result := True;
#if PackageType == "AppUpdate"
  Result := BackupExisting('YOLOTool.exe') and
    BackupExisting('app_assets') and
    BackupExisting('app-version.txt') and
    BackupExisting('package-info.ini') and
    BackupExisting('release-manifest.json') and
    BackupExisting('runtime-manifest.json') and
    BackupExisting('runtime-version.txt') and
    MoveStaged('YOLOTool.exe') and
    MoveStaged('app_assets') and
    MoveStaged('app-version.txt') and
    MoveStaged('package-info.ini') and
    MoveStaged('release-manifest.json') and
    MoveStaged('runtime-manifest.json') and
    MoveStaged('runtime-version.txt');
#endif
#if PackageType == "RuntimeFull"
  Result := BackupExisting('YOLOTool.exe') and
    BackupExisting('app_assets') and
    BackupExisting('app-version.txt') and
    MoveStaged('YOLOTool.exe') and
    MoveStaged('app_assets') and
    MoveStaged('app-version.txt');
  if Result then
    Result := BackupExisting('_internal') and
      BackupExisting('package-info.ini') and
      BackupExisting('release-manifest.json') and
      BackupExisting('runtime-manifest.json') and
      BackupExisting('runtime-version.txt') and
      MoveStaged('_internal') and
      MoveStaged('package-info.ini') and
      MoveStaged('release-manifest.json') and
      MoveStaged('runtime-manifest.json') and
      MoveStaged('runtime-version.txt');
#endif
end;

procedure CleanupUpdateArtifacts();
var
  ExitCode: Integer;
begin
  RunHiddenCommand('rmdir /S /Q "' + ExpandConstant('{app}\.update-working') + '"', ExitCode);
  RunHiddenCommand('rmdir /S /Q "' + ExpandConstant('{app}\.update-backup') + '"', ExitCode);
end;

function RestoreUpdate(): Boolean;
begin
  Result := True;
#if PackageType == "AppUpdate"
  Result := RestoreExisting('YOLOTool.exe') and RestoreExisting('app_assets') and
    RestoreExisting('app-version.txt') and RestoreExisting('package-info.ini') and
    RestoreExisting('release-manifest.json') and
    RestoreExisting('runtime-manifest.json') and RestoreExisting('runtime-version.txt');
#endif
#if PackageType == "RuntimeFull"
  Result := RestoreExisting('YOLOTool.exe') and RestoreExisting('app_assets') and
    RestoreExisting('app-version.txt') and
    RestoreExisting('_internal') and RestoreExisting('package-info.ini') and
    RestoreExisting('release-manifest.json') and
    RestoreExisting('runtime-manifest.json') and RestoreExisting('runtime-version.txt');
#endif
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  InstalledRuntime: String;
begin
  Result := '';
#if PackageType != "Full"
  if not PreviousInstallExists() then
  begin
    Result := '未找到已有 YOLOTool 安装，请先安装完整安装包。';
    exit;
  end;

  if DirExists(ExpandConstant('{app}\.update-working')) or
     DirExists(ExpandConstant('{app}\.update-backup')) then
  begin
    Result := '检测到上一次更新留下的临时文件，请先确认旧版本可以启动后再重试。';
    exit;
  end;

  InstalledRuntime := ReadInstalledRuntimeVersion();
#if PackageType == "AppUpdate"
  if ('{#RequiredRuntimeVersion}' <> '') and
     (InstalledRuntime <> '{#RequiredRuntimeVersion}') then
  begin
    Result := '当前运行环境版本为 ' + InstalledRuntime +
      '，程序更新包要求 ' + '{#RequiredRuntimeVersion}' +
      '。请先安装匹配的环境更新包。';
    exit;
  end;
#endif
#endif
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
#if PackageType != "Full"
  if CurStep = ssPostInstall then
  begin
    if not CommitUpdate() then
    begin
      MsgBox('更新文件切换失败，安装程序将尝试恢复旧版本。', mbError, MB_OK);
      Abort;
    end;
    UpdateCommitted := True;
    CleanupUpdateArtifacts();
  end;
#endif
end;

procedure DeinitializeSetup();
begin
#if PackageType != "Full"
  if UpdateCommitStarted and not UpdateCommitted then
  begin
    if RestoreUpdate() then
      CleanupUpdateArtifacts()
    else
      MsgBox('更新失败且无法自动恢复，请保留 .update-backup 目录并联系维护人员。', mbError, MB_OK);
  end;
#endif
end;

procedure CurPageChanged(CurPageID: Integer);
begin
#if PackageType == "Full"
  if (CurPageID = wpSelectDir) and PreviousInstallExists() then
  begin
    WizardForm.DirEdit.ReadOnly := True;
    WizardForm.DirBrowseButton.Enabled := False;
  end;
#endif
end;
