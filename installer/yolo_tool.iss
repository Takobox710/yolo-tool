#ifndef MyAppVersion
#define MyAppVersion "1.3.2"
#endif
#ifndef RequiredRuntimeVersion
#define RequiredRuntimeVersion "runtime-2"
#endif
#ifndef BasePackageName
#define BasePackageName ""
#endif
#ifndef BasePackageHash
#define BasePackageHash ""
#endif
#ifndef BaseCompressedSize
#define BaseCompressedSize "0"
#endif
#ifndef BasePackageVersion
#define BasePackageVersion ""
#endif
#ifndef BaseRuntimeVersion
#define BaseRuntimeVersion ""
#endif
#ifndef BaseUnpackedSize
#define BaseUnpackedSize "0"
#endif
#ifndef ExtensionPackageName
#define ExtensionPackageName ""
#endif
#ifndef ExtensionPackageHash
#define ExtensionPackageHash ""
#endif
#ifndef ExtensionCompressedSize
#define ExtensionCompressedSize "0"
#endif
#ifndef ExtensionPackageVersion
#define ExtensionPackageVersion ""
#endif
#define GitHubReleaseUrl "https://github.com/Takobox710/yolo-tool/releases"

#define MyAppName "YOLOTool"
#define MyAppPublisher "Takobox"
#define MyAppExeName "YOLOTool.exe"
#define LegacyAppId "{AFD7B4C3-5B11-4F8D-8BA1-64D96FD3C4A1}"
#define LegacyUninstallKey "Software\Microsoft\Windows\CurrentVersion\Uninstall\{AFD7B4C3-5B11-4F8D-8BA1-64D96FD3C4A1}_is1"
#define MetadataRelativeRoot "_internal\yolotool_metadata"

[Setup]
AppId={{AFD7B4C3-5B11-4F8D-8BA1-64D96FD3C4A1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={code:GetDefaultAppDir}
DisableDirPage=no
UsePreviousAppDir=no
DirExistsWarning=no
UsePreviousLanguage=no
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=output
OutputBaseFilename={#MyAppName}_Setup_{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
ArchiveExtraction=enhanced/nopassword
WizardStyle=modern
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
CloseApplications=force
CloseApplicationsFilter=YOLOTool.exe
RestartApplications=no
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=commandline
SetupIconFile=..\src\assets\app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Uninstallable=yes
CreateUninstallRegKey=no

[Languages]
Name: "chinesesimp"; MessagesFile: "languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务:"; Flags: unchecked

[Dirs]
Name: "{app}\data\models"
Name: "{app}\data\runtime"
Name: "{app}\images"
Name: "{app}\labels"
Name: "{app}\result"

[Files]
Source: "..\dist\packages\Program\YOLOTool.exe"; DestDir: "{app}\.install-staging\program"; Flags: ignoreversion
Source: "..\dist\packages\Program\app-version.txt"; DestDir: "{app}\.install-staging\program"; Flags: ignoreversion
Source: "..\dist\packages\Program\release-manifest.json"; DestDir: "{app}\.install-staging\program"; Flags: ignoreversion
Source: "..\dist\packages\Program\program-package-info.ini"; DestDir: "{app}\.install-staging\program"; Flags: ignoreversion
Source: "..\dist\packages\Program\companion-catalog.json"; DestDir: "{app}\.install-staging\program"; Flags: ignoreversion
Source: "{code:GetBaseArchivePath}"; DestDir: "{app}\.install-staging\base"; ExternalSize: {#BaseUnpackedSize}; Flags: external extractarchive recursesubdirs createallsubdirs ignoreversion; Check: ShouldInstallBase

[Icons]
Name: "{group}\{code:GetShortcutName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{code:GetShortcutName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent; Check: MainInstallSucceeded
Filename: "{cmd}"; Parameters: "{code:GetCleanupParameters}"; Description: "安装完成后删除本次使用的安装包和环境包"; Flags: runhidden postinstall unchecked skipifsilent; Check: MainInstallSucceeded

[UninstallDelete]
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{app}\.install-staging"
Type: filesandordirs; Name: "{app}\.install-backup"
Type: files; Name: "{app}\YOLOTool.exe"
Type: files; Name: "{app}\yolo26n.pt"
Type: files; Name: "{app}\app-version.txt"
Type: files; Name: "{app}\release-manifest.json"
Type: files; Name: "{app}\runtime-manifest.json"
Type: files; Name: "{app}\runtime-version.txt"
Type: files; Name: "{app}\base-package-manifest.json"
Type: files; Name: "{app}\managed-models.json"
Type: files; Name: "{app}\package-info.ini"
Type: files; Name: "{app}\install-instance.ini"
Type: files; Name: "{app}\unins000.exe"
Type: files; Name: "{app}\unins000.dat"
Type: files; Name: "{app}\uninstall.exe"
Type: files; Name: "{app}\uninstall.dat"

[Code]
var
  ComponentsPage: TWizardPage;
  ProgramCheck: TNewCheckBox;
  ProgramStatus: TNewStaticText;
  BaseCheck: TNewCheckBox;
  BaseStatus: TNewStaticText;
  BasePathEdit: TNewEdit;
  BaseBrowseButton: TNewButton;
  BaseGithubButton: TNewButton;
  ExtensionCheck: TNewCheckBox;
  ExtensionStatus: TNewStaticText;
  ExtensionPathEdit: TNewEdit;
  ExtensionBrowseButton: TNewButton;
  BaseArchivePath: String;
  ExtensionArchivePath: String;
  ExistingAppVersion: String;
  ExistingRuntimeVersion: String;
  ExistingBaseVersion: String;
  ExistingExtensionVersion: String;
  BaseIsRequired: Boolean;
  ExistingInstall: Boolean;
  DowngradeConfirmed: Boolean;
  UpdateCommitStarted: Boolean;
  UpdateCommitted: Boolean;
  RollbackPerformed: Boolean;
  ExtensionPreserved: Boolean;
  WizardInitialized: Boolean;
  TransactionInitialized: Boolean;
  TransactionAppDir: String;
  RootModelTouched: Boolean;
  BaseArchiveChecked: Boolean;
  BaseArchiveValid: Boolean;
  BaseArchiveHashVerified: Boolean;
  ExtensionArchiveChecked: Boolean;
  ExtensionArchiveValid: Boolean;
  ExtensionArchiveHashVerified: Boolean;
  VerificationPage: TOutputProgressWizardPage;

function NormalizeInstallPath(const Value: String): String;
begin
  Result := Lowercase(RemoveBackslashUnlessRoot(ExpandFileName(Value)));
end;

function PathInstanceId(const Value: String): String;
begin
  Result := GetMD5OfString(NormalizeInstallPath(Value));
end;

function TryGetLegacyInstallDir(var InstallDir: String): Boolean;
begin
  Result :=
    RegQueryStringValue(HKLM64, '{#LegacyUninstallKey}', 'InstallLocation', InstallDir) or
    RegQueryStringValue(HKLM32, '{#LegacyUninstallKey}', 'InstallLocation', InstallDir) or
    RegQueryStringValue(HKCU64, '{#LegacyUninstallKey}', 'InstallLocation', InstallDir) or
    RegQueryStringValue(HKCU32, '{#LegacyUninstallKey}', 'InstallLocation', InstallDir);
end;

function IsLegacyInstallPath(const Value: String): Boolean;
var
  LegacyPath: String;
begin
  Result := TryGetLegacyInstallDir(LegacyPath) and
    (NormalizeInstallPath(LegacyPath) = NormalizeInstallPath(Value));
end;

function IsRecognizableInstallPath(const Value: String): Boolean;
var
  Normalized: String;
begin
  Normalized := RemoveBackslashUnlessRoot(ExpandFileName(Value));
  Result := FileExists(AddBackslash(Normalized) + '{#MyAppExeName}') and
    DirExists(AddBackslash(Normalized) + '_internal');
end;

function GetDefaultAppDir(Param: String): String;
var
  Candidate: String;
begin
  if RegQueryStringValue(HKCU, 'Software\YOLOTool\Installer',
    'LastInstallPath', Candidate) then
  begin
    if IsRecognizableInstallPath(Candidate) then
    begin
      Result := Candidate;
      exit;
    end;
    RegDeleteValue(HKCU, 'Software\YOLOTool\Installer', 'LastInstallPath');
  end;
  if TryGetLegacyInstallDir(Candidate) and IsRecognizableInstallPath(Candidate) then
    Result := Candidate
  else
    Result := ExpandConstant('{autopf}\{#MyAppName}');
end;

function GetShortcutName(Param: String): String;
var
  FolderName: String;
begin
  FolderName := ExtractFileName(RemoveBackslashUnlessRoot(ExpandConstant('{app}')));
  if CompareText(FolderName, '{#MyAppName}') = 0 then
    Result := '{#MyAppName}'
  else
    Result := '{#MyAppName} - ' + FolderName;
end;

function ReadTextFile(const FileName: String): String;
var
  Buffer: AnsiString;
begin
  Result := '';
  if LoadStringFromFile(FileName, Buffer) then
    Result := Trim(String(Buffer));
end;

function MetadataRelativePath(const FileName: String): String;
begin
  Result := '{#MetadataRelativeRoot}\' + FileName;
end;

function InstalledMetadataPath(const FileName: String): String;
begin
  Result := ExpandConstant('{app}\') + MetadataRelativePath(FileName);
end;

function ResolveInstalledMetadataPath(const FileName: String): String;
begin
  Result := InstalledMetadataPath(FileName);
  if not FileExists(Result) then
    Result := ExpandConstant('{app}\') + FileName;
end;

function ReadInstalledValue(const Key, DefaultValue: String): String;
begin
  Result := GetIniString('Package', Key, DefaultValue,
    ResolveInstalledMetadataPath('package-info.ini'));
end;

function CurrentInstanceId(): String;
begin
  Result := GetIniString('Install', 'instance_id', '',
    ResolveInstalledMetadataPath('install-instance.ini'));
  if Result = '' then
    Result := PathInstanceId(ExpandConstant('{app}'));
end;

function InstanceExtensionRoot(): String;
begin
  Result := ExpandConstant('{app}\_internal\extensions');
end;

function LegacyInstanceExtensionRoot(): String;
begin
  Result := ExpandConstant('{localappdata}\YOLOTool\instances\') +
    CurrentInstanceId() + '\extensions';
end;

function ReadExtensionVersionAt(const Root: String): String;
begin
  Result := GetIniString('Extension', 'active_version', '',
    AddBackslash(Root) + 'model-export-runtime\active.ini');
end;

function IsArchiveCandidate(const FileName, ExpectedName,
  ExpectedSize: String): Boolean;
var
  ActualSize: Int64;
begin
  Result := False;
  if (FileName = '') or (ExpectedName = '') or not FileExists(FileName) then
    exit;
  if CompareText(ExtractFileName(FileName), ExpectedName) <> 0 then
    exit;
  if CompareText(ExtractFileExt(FileName), '.7z') <> 0 then
    exit;
  Result := FileSize64(FileName, ActualSize) and
    (ActualSize = StrToInt64Def(ExpectedSize, -1));
end;

function VerifyArchiveHash(const FileName, ExpectedHash: String): Boolean;
begin
  Result := False;
  if (FileName = '') or (ExpectedHash = '') or not FileExists(FileName) then
    exit;
  try
    Result := CompareText(GetSHA256OfFile(FileName), ExpectedHash) = 0;
  except
    Result := False;
  end;
end;

procedure BeginArchiveVerification(const Message: String);
begin
  if VerificationPage <> nil then
  begin
    VerificationPage.SetText(Message,
      '正在读取压缩包 SHA-256 校验值，请稍候...');
    VerificationPage.SetProgress(0, 1);
    VerificationPage.Show;
  end;
  WizardForm.StatusLabel.Caption := Message;
  WizardForm.FilenameLabel.Caption := '正在读取压缩包校验值，请稍候...';
  WizardForm.ProgressGauge.Style := npbstMarquee;
  WizardForm.ProgressGauge.Visible := True;
  WizardForm.Update;
end;

procedure EndArchiveVerification();
begin
  if VerificationPage <> nil then
  begin
    VerificationPage.SetProgress(1, 1);
    VerificationPage.Hide;
  end;
  WizardForm.ProgressGauge.Style := npbstNormal;
  WizardForm.ProgressGauge.Position := 0;
  WizardForm.FilenameLabel.Caption := '';
  WizardForm.Update;
end;

function IsValidBaseArchive(): Boolean;
begin
  if not BaseArchiveChecked then
  begin
    BaseArchiveValid := IsArchiveCandidate(BaseArchivePath,
      '{#BasePackageName}', '{#BaseCompressedSize}');
    BaseArchiveChecked := True;
  end;
  Result := BaseArchiveValid;
end;

function IsValidExtensionArchive(): Boolean;
begin
  if not ExtensionArchiveChecked then
  begin
    ExtensionArchiveValid := IsArchiveCandidate(ExtensionArchivePath,
      '{#ExtensionPackageName}', '{#ExtensionCompressedSize}');
    ExtensionArchiveChecked := True;
  end;
  Result := ExtensionArchiveValid;
end;

function NextVersionPart(const Version: String; var Position: Integer): Integer;
var
  Start: Integer;
  Part: String;
begin
  Start := Position;
  while (Position <= Length(Version)) and (Version[Position] <> '.') do
    Position := Position + 1;
  Part := Copy(Version, Start, Position - Start);
  Position := Position + 1;
  Result := StrToIntDef(Part, 0);
end;

function CompareVersions(const LeftVersion, RightVersion: String): Integer;
var
  I, LeftPosition, RightPosition, LeftPart, RightPart: Integer;
begin
  Result := 0;
  LeftPosition := 1;
  RightPosition := 1;
  for I := 1 to 4 do
  begin
    LeftPart := NextVersionPart(LeftVersion, LeftPosition);
    RightPart := NextVersionPart(RightVersion, RightPosition);
    if LeftPart < RightPart then
    begin
      Result := -1;
      exit;
    end;
    if LeftPart > RightPart then
    begin
      Result := 1;
      exit;
    end;
  end;
end;

procedure DetectInstalledState();
var
  LegacyExtensionVersion: String;
begin
  ExistingAppVersion := ReadInstalledValue('app_version',
    ReadTextFile(ResolveInstalledMetadataPath('app-version.txt')));
  ExistingRuntimeVersion := ReadInstalledValue('runtime_version',
    ReadTextFile(ExpandConstant('{app}\runtime-version.txt')));
  ExistingBaseVersion := ReadInstalledValue('base_package_version', '');
  ExistingInstall := FileExists(ExpandConstant('{app}\{#MyAppExeName}')) and
    DirExists(ExpandConstant('{app}\_internal'));
  ExistingExtensionVersion := ReadExtensionVersionAt(InstanceExtensionRoot());
  if ExistingExtensionVersion = '' then
  begin
    LegacyExtensionVersion := ReadExtensionVersionAt(LegacyInstanceExtensionRoot());
    if LegacyExtensionVersion = '' then
      LegacyExtensionVersion := ReadExtensionVersionAt(
        ExpandConstant('{localappdata}\YOLOTool\extensions'));
    if ExistingInstall then
      ExistingExtensionVersion := LegacyExtensionVersion;
  end;
  BaseIsRequired := (not ExistingInstall) or
    (ExistingRuntimeVersion <> '{#RequiredRuntimeVersion}') or
    not FileExists(ResolveInstalledMetadataPath('runtime-manifest.json')) or
    not FileExists(ExpandConstant('{app}\data\models\yolo26n.pt'));
end;

procedure RefreshComponentPage();
var
  VersionComparison: Integer;
begin
  DetectInstalledState();
  if not ExistingInstall then
    ProgramStatus.Caption := '将安装程序本体 {#MyAppVersion}'
  else
  begin
    VersionComparison := CompareVersions(ExistingAppVersion, '{#MyAppVersion}');
    if VersionComparison < 0 then
      ProgramStatus.Caption := '程序本体：' + ExistingAppVersion + ' 更新至 {#MyAppVersion}'
    else if VersionComparison = 0 then
      ProgramStatus.Caption := '修复安装程序本体 {#MyAppVersion}'
    else
      ProgramStatus.Caption := '程序本体：' + ExistingAppVersion + ' 降级至 {#MyAppVersion}（需要确认）';
  end;

  BaseCheck.Checked := BaseIsRequired and IsValidBaseArchive();
  BaseCheck.Enabled := (not BaseIsRequired) and IsValidBaseArchive();
  BasePathEdit.Text := BaseArchivePath;
  if IsValidBaseArchive() then
  begin
    BaseStatus.Font.Color := clGreen;
    if BaseIsRequired then
      BaseStatus.Caption := '已找到必需基础包 {#BasePackageVersion}，安装时将进行完整校验。'
    else
      BaseStatus.Caption := '当前环境 ' + ExistingRuntimeVersion +
        ' 可继续使用；已找到基础包，安装时将进行完整校验。';
  end
  else
  begin
    BaseStatus.Font.Color := clRed;
    if BaseIsRequired and not ExistingInstall then
      BaseStatus.Caption := '首次安装必须提供匹配的基础环境和模型包，当前无法继续。'
    else if BaseIsRequired then
      BaseStatus.Caption := '未找到匹配基础环境包，将继续使用旧环境；可能导致部分功能缺失。'
    else
      BaseStatus.Caption := '未找到合法基础包，本次将保留现有运行环境。';
  end;
  BaseGithubButton.Visible := BaseIsRequired and not IsValidBaseArchive();

  ExtensionCheck.Checked := False;
  ExtensionCheck.Enabled := IsValidExtensionArchive();
  ExtensionPathEdit.Text := ExtensionArchivePath;
  if IsValidExtensionArchive() then
  begin
    ExtensionStatus.Font.Color := clGreen;
    if ExistingExtensionVersion <> '' then
      ExtensionStatus.Caption := '已安装 ' + ExistingExtensionVersion +
        '；可选替换为 {#ExtensionPackageVersion}，安装时将进行完整校验。'
    else
      ExtensionStatus.Caption := '检测到可选附加包 {#ExtensionPackageVersion}，安装时将进行完整校验。';
  end
  else
  begin
    ExtensionStatus.Font.Color := clRed;
    if ExistingExtensionVersion <> '' then
      ExtensionStatus.Caption := '当前已安装 ' + ExistingExtensionVersion +
        '；未找到新的附加包，本次保持不变。'
    else
      ExtensionStatus.Caption := '未找到合法模型转换附加包，可跳过安装。';
  end;
end;

procedure BrowseBaseClick(Sender: TObject);
var
  Selected: String;
begin
  Selected := BaseArchivePath;
  if GetOpenFileName('选择本体环境和模型包', Selected,
    ExtractFileDir(Selected), '7z 压缩包|*.7z', '7z') then
  begin
    BaseArchivePath := Selected;
    BaseArchiveChecked := False;
    BaseArchiveHashVerified := False;
    RefreshComponentPage();
  end;
end;

procedure BrowseExtensionClick(Sender: TObject);
var
  Selected: String;
begin
  Selected := ExtensionArchivePath;
  if GetOpenFileName('选择模型转换附加包', Selected,
    ExtractFileDir(Selected), '7z 压缩包|*.7z', '7z') then
  begin
    ExtensionArchivePath := Selected;
    ExtensionArchiveChecked := False;
    ExtensionArchiveHashVerified := False;
    RefreshComponentPage();
  end;
end;

procedure OpenGitHubReleaseClick(Sender: TObject);
var
  ErrorCode: Integer;
begin
  ShellExec('open', '{#GitHubReleaseUrl}', '', '', SW_SHOWNORMAL,
    ewNoWait, ErrorCode);
end;

procedure InitializeWizard();
var
  Top: Integer;
begin
  BaseArchivePath := ExpandConstant('{src}\{#BasePackageName}');
  ExtensionArchivePath := ExpandConstant('{src}\{#ExtensionPackageName}');
  ComponentsPage := CreateCustomPage(wpSelectDir, '选择安装组件',
    '程序本体固定安装，其他组件根据当前目录和本地压缩包状态选择。');

  Top := 8;
  ProgramCheck := TNewCheckBox.Create(ComponentsPage);
  ProgramCheck.Parent := ComponentsPage.Surface;
  ProgramCheck.Top := Top;
  ProgramCheck.Width := ComponentsPage.SurfaceWidth;
  ProgramCheck.Caption := '程序本体';
  ProgramCheck.Checked := True;
  ProgramCheck.Enabled := False;
  ProgramStatus := TNewStaticText.Create(ComponentsPage);
  ProgramStatus.Parent := ComponentsPage.Surface;
  ProgramStatus.Top := Top + 24;
  ProgramStatus.Width := ComponentsPage.SurfaceWidth;

  Top := Top + 62;
  BaseCheck := TNewCheckBox.Create(ComponentsPage);
  BaseCheck.Parent := ComponentsPage.Surface;
  BaseCheck.Top := Top;
  BaseCheck.Width := ComponentsPage.SurfaceWidth;
  BaseCheck.Caption := '本体环境和模型';
  BasePathEdit := TNewEdit.Create(ComponentsPage);
  BasePathEdit.Parent := ComponentsPage.Surface;
  BasePathEdit.Top := Top + 24;
  BasePathEdit.Width := ComponentsPage.SurfaceWidth - 86;
  BasePathEdit.ReadOnly := True;
  BaseBrowseButton := TNewButton.Create(ComponentsPage);
  BaseBrowseButton.Parent := ComponentsPage.Surface;
  BaseBrowseButton.Top := Top + 22;
  BaseBrowseButton.Left := ComponentsPage.SurfaceWidth - 78;
  BaseBrowseButton.Width := 78;
  BaseBrowseButton.Caption := '浏览...';
  BaseBrowseButton.OnClick := @BrowseBaseClick;
  BaseStatus := TNewStaticText.Create(ComponentsPage);
  BaseStatus.Parent := ComponentsPage.Surface;
  BaseStatus.Top := Top + 52;
  BaseStatus.Width := ComponentsPage.SurfaceWidth;
  BaseStatus.AutoSize := False;
  BaseStatus.WordWrap := True;
  BaseStatus.Height := 32;
  BaseStatus.Width := ComponentsPage.SurfaceWidth - 164;
  BaseGithubButton := TNewButton.Create(ComponentsPage);
  BaseGithubButton.Parent := ComponentsPage.Surface;
  BaseGithubButton.Top := Top + 54;
  BaseGithubButton.Left := ComponentsPage.SurfaceWidth - 154;
  BaseGithubButton.Width := 154;
  BaseGithubButton.Height := 26;
  BaseGithubButton.Caption := '进入 GitHub 下载';
  BaseGithubButton.OnClick := @OpenGitHubReleaseClick;

  Top := Top + 126;
  ExtensionCheck := TNewCheckBox.Create(ComponentsPage);
  ExtensionCheck.Parent := ComponentsPage.Surface;
  ExtensionCheck.Top := Top;
  ExtensionCheck.Width := ComponentsPage.SurfaceWidth;
  ExtensionCheck.Caption := '模型转换附加环境（可选）';
  ExtensionPathEdit := TNewEdit.Create(ComponentsPage);
  ExtensionPathEdit.Parent := ComponentsPage.Surface;
  ExtensionPathEdit.Top := Top + 24;
  ExtensionPathEdit.Width := ComponentsPage.SurfaceWidth - 86;
  ExtensionPathEdit.ReadOnly := True;
  ExtensionBrowseButton := TNewButton.Create(ComponentsPage);
  ExtensionBrowseButton.Parent := ComponentsPage.Surface;
  ExtensionBrowseButton.Top := Top + 22;
  ExtensionBrowseButton.Left := ComponentsPage.SurfaceWidth - 78;
  ExtensionBrowseButton.Width := 78;
  ExtensionBrowseButton.Caption := '浏览...';
  ExtensionBrowseButton.OnClick := @BrowseExtensionClick;
  ExtensionStatus := TNewStaticText.Create(ComponentsPage);
  ExtensionStatus.Parent := ComponentsPage.Surface;
  ExtensionStatus.Top := Top + 52;
  ExtensionStatus.Width := ComponentsPage.SurfaceWidth;
  ExtensionStatus.AutoSize := False;
  ExtensionStatus.WordWrap := True;
  ExtensionStatus.Height := 34;
  VerificationPage := CreateOutputProgressPage('正在验证安装包',
    '安装程序即将验证本地环境包，请稍候...');
  WizardInitialized := True;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = ComponentsPage.ID then
    RefreshComponentPage();
end;

function ShouldInstallBase(): Boolean; forward;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = ComponentsPage.ID then
  begin
    if (not ExistingInstall) and BaseIsRequired and
      not IsValidBaseArchive() then
    begin
      Result := False;
      MsgBox('首次安装必须提供匹配的本体环境和模型包。' + #13#10 +
        '请先准备基础环境包后再继续安装。', mbError, MB_OK);
      exit;
    end;
    if ExistingInstall and
      (CompareVersions(ExistingAppVersion, '{#MyAppVersion}') > 0) and
      not DowngradeConfirmed then
    begin
      Result := MsgBox('目标目录中的程序版本为 ' + ExistingAppVersion +
        '，高于当前安装器 {#MyAppVersion}。确定继续降级吗？',
        mbConfirmation, MB_YESNO) = IDYES;
      DowngradeConfirmed := Result;
    end;
  end;
end;

function ShouldInstallBase(): Boolean;
begin
  Result := BaseCheck.Checked;
end;

function GetCleanupParameters(Param: String): String;
begin
  Result := '/C ping 127.0.0.1 -n 3 > nul & del /f /q "' +
    ExpandConstant('{srcexe}') + '"';
  if ShouldInstallBase() then
    Result := Result + ' & del /f /q "' + BaseArchivePath + '"';
  if ExtensionCheck.Checked then
    Result := Result + ' & del /f /q "' + ExtensionArchivePath + '"';
end;

function GetBaseArchivePath(Param: String): String;
begin
  Result := BaseArchivePath;
end;

function ProgramStagePath(const RelativePath: String): String;
begin
  Result := ExpandConstant('{app}\.install-staging\program\') + RelativePath;
end;

function BaseStagePath(const RelativePath: String): String;
begin
  Result := ExpandConstant('{app}\.install-staging\base\') + RelativePath;
end;

function BackupPath(const RelativePath: String): String;
begin
  Result := ExpandConstant('{app}\.install-backup\') + RelativePath;
end;

function MissingMarkerPath(const RelativePath: String): String;
begin
  Result := BackupPath(RelativePath) + '.missing';
end;

function RemoveTarget(const RelativePath: String): Boolean;
var
  Target: String;
begin
  Target := ExpandConstant('{app}\') + RelativePath;
  if FileExists(Target) then
    Result := DeleteFile(Target)
  else if DirExists(Target) then
    Result := DelTree(Target, True, True, True)
  else
    Result := True;
end;

function BackupExisting(const RelativePath: String): Boolean;
var
  Source, Destination: String;
begin
  Source := ExpandConstant('{app}\') + RelativePath;
  Destination := BackupPath(RelativePath);
  if not (FileExists(Source) or DirExists(Source)) then
  begin
    ForceDirectories(ExtractFileDir(Destination));
    Result := SaveStringToFile(MissingMarkerPath(RelativePath), '', False);
    exit;
  end;
  ForceDirectories(ExtractFileDir(Destination));
  Result := RenameFile(Source, Destination);
end;

function MoveStaged(const Source, RelativePath: String): Boolean;
var
  Destination: String;
begin
  Destination := ExpandConstant('{app}\') + RelativePath;
  ForceDirectories(ExtractFileDir(Destination));
  Result := RenameFile(Source, Destination);
end;

function RestoreExisting(const RelativePath: String): Boolean;
var
  Source, Destination: String;
begin
  Source := BackupPath(RelativePath);
  Destination := ExpandConstant('{app}\') + RelativePath;
  if FileExists(Source) or DirExists(Source) then
  begin
    RemoveTarget(RelativePath);
    ForceDirectories(ExtractFileDir(Destination));
    Result := RenameFile(Source, Destination);
    exit;
  end;
  if FileExists(MissingMarkerPath(RelativePath)) then
  begin
    Result := RemoveTarget(RelativePath);
    DeleteFile(MissingMarkerPath(RelativePath));
  end
  else
    Result := True;
end;

function MergeModelDirectory(const SourceRoot, SourceDirectory, RelativeDirectory: String): Boolean;
var
  FindRec: TFindRec;
  SourcePath, RelativePath, Destination, Backup: String;
begin
  Result := True;
  if not FindFirst(AddBackslash(SourceDirectory) + '*', FindRec) then
    exit;
  try
    repeat
      if (FindRec.Name <> '.') and (FindRec.Name <> '..') then
      begin
        SourcePath := AddBackslash(SourceDirectory) + FindRec.Name;
        if RelativeDirectory = '' then
          RelativePath := FindRec.Name
        else
          RelativePath := AddBackslash(RelativeDirectory) + FindRec.Name;
        if (FindRec.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0 then
          Result := MergeModelDirectory(SourceRoot, SourcePath, RelativePath)
        else
        begin
          Destination := ExpandConstant('{app}\data\models\') + RelativePath;
          Backup := BackupPath('data\models\' + RelativePath);
          ForceDirectories(ExtractFileDir(Destination));
          if FileExists(Destination) then
          begin
            ForceDirectories(ExtractFileDir(Backup));
            if not RenameFile(Destination, Backup) then
              Result := False;
          end;
          if Result and not FileExists(Backup) then
          begin
            ForceDirectories(ExtractFileDir(Backup));
            Result := SaveStringToFile(Backup + '.missing', '', False);
          end;
          if Result and not CopyFile(SourcePath, Destination, False) then
            Result := False;
        end;
        if not Result then
          exit;
      end;
    until not FindNext(FindRec);
  finally
    FindClose(FindRec);
  end;
end;

function MergeModels(): Boolean;
var
  Source: String;
begin
  Source := BaseStagePath('data\models');
  if not DirExists(Source) then
    Result := True
  else
    Result := MergeModelDirectory(Source, Source, '');
end;

function RestoreMergedModelDirectory(const SourceDirectory,
  RelativeDirectory: String): Boolean;
var
  FindRec: TFindRec;
  SourcePath, RelativePath, Destination, Backup: String;
begin
  Result := True;
  if not FindFirst(AddBackslash(SourceDirectory) + '*', FindRec) then
    exit;
  try
    repeat
      if (FindRec.Name <> '.') and (FindRec.Name <> '..') then
      begin
        SourcePath := AddBackslash(SourceDirectory) + FindRec.Name;
        if RelativeDirectory = '' then
          RelativePath := FindRec.Name
        else
          RelativePath := AddBackslash(RelativeDirectory) + FindRec.Name;
        if (FindRec.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0 then
          Result := RestoreMergedModelDirectory(SourcePath, RelativePath)
        else
        begin
          Destination := ExpandConstant('{app}\data\models\') + RelativePath;
          Backup := BackupPath('data\models\' + RelativePath);
          if FileExists(Backup) then
          begin
            if FileExists(Destination) and not DeleteFile(Destination) then
              Result := False;
            ForceDirectories(ExtractFileDir(Destination));
            if Result then
              Result := RenameFile(Backup, Destination);
          end
          else if FileExists(Backup + '.missing') then
          begin
            if FileExists(Destination) and not DeleteFile(Destination) then
              Result := False;
            DeleteFile(Backup + '.missing');
          end;
        end;
        if not Result then
          exit;
      end;
    until not FindNext(FindRec);
  finally
    FindClose(FindRec);
  end;
end;

function RestoreMergedModels(): Boolean;
var
  Source: String;
begin
  Source := BaseStagePath('data\models');
  if not DirExists(Source) then
    Result := True
  else
    Result := RestoreMergedModelDirectory(Source, '');
end;

function BackupLegacyMetadata(): Boolean;
begin
  Result := BackupExisting('app-version.txt') and
    BackupExisting('release-manifest.json') and
    BackupExisting('runtime-manifest.json') and
    BackupExisting('runtime-version.txt') and
    BackupExisting('base-package-manifest.json') and
    BackupExisting('managed-models.json') and
    BackupExisting('package-info.ini') and
    BackupExisting('install-instance.ini');
end;

function BackupProgramMetadata(): Boolean;
begin
  Result := BackupExisting(MetadataRelativePath('app-version.txt')) and
    BackupExisting(MetadataRelativePath('release-manifest.json')) and
    BackupExisting(MetadataRelativePath('package-info.ini')) and
    BackupExisting(MetadataRelativePath('install-instance.ini'));
end;

function MarkMetadataMissing(const FileName: String): Boolean;
var
  RelativePath: String;
begin
  RelativePath := MetadataRelativePath(FileName);
  if FileExists(ExpandConstant('{app}\') + RelativePath) then
    Result := True
  else
  begin
    ForceDirectories(ExtractFileDir(MissingMarkerPath(RelativePath)));
    Result := SaveStringToFile(MissingMarkerPath(RelativePath), '', False);
  end;
end;

function CopyLegacyMetadataIfMissing(const FileName: String): Boolean;
var
  Source, Destination: String;
begin
  Destination := InstalledMetadataPath(FileName);
  if FileExists(Destination) then
  begin
    Result := True;
    exit;
  end;
  Source := BackupPath(FileName);
  if not FileExists(Source) then
  begin
    Result := True;
    exit;
  end;
  ForceDirectories(ExtractFileDir(Destination));
  Result := CopyFile(Source, Destination, False);
end;

function MigrateLegacyBaseMetadata(): Boolean;
begin
  Result := MarkMetadataMissing('runtime-manifest.json') and
    MarkMetadataMissing('base-package-manifest.json') and
    MarkMetadataMissing('managed-models.json') and
    CopyLegacyMetadataIfMissing('runtime-manifest.json') and
    CopyLegacyMetadataIfMissing('base-package-manifest.json') and
    CopyLegacyMetadataIfMissing('managed-models.json');
end;

function PrepareRootModel(): Boolean;
var
  Source, Destination: String;
begin
  Destination := ExpandConstant('{app}\yolo26n.pt');
  if ShouldInstallBase() then
    Source := BaseStagePath('data\models\yolo26n.pt')
  else
  begin
    if FileExists(Destination) then
    begin
      Result := True;
      exit;
    end;
    Source := ExpandConstant('{app}\data\models\yolo26n.pt');
  end;
  if not FileExists(Source) then
  begin
    Result := False;
    exit;
  end;
  if not RootModelTouched then
  begin
    Result := BackupExisting('yolo26n.pt');
    if not Result then
      exit;
    RootModelTouched := True;
  end;
  Result := CopyFile(Source, Destination, False);
end;

procedure WriteInstallState();
var
  RuntimeVersion, BaseVersion: String;
begin
  if ShouldInstallBase() then
  begin
    RuntimeVersion := '{#BaseRuntimeVersion}';
    BaseVersion := '{#BasePackageVersion}';
  end
  else
  begin
    RuntimeVersion := ExistingRuntimeVersion;
    BaseVersion := ExistingBaseVersion;
  end;
  ForceDirectories(ExpandConstant('{app}\{#MetadataRelativeRoot}'));
  SetIniString('Package', 'type', 'Program', InstalledMetadataPath('package-info.ini'));
  SetIniString('Package', 'app_version', '{#MyAppVersion}', InstalledMetadataPath('package-info.ini'));
  SetIniString('Package', 'runtime_version', RuntimeVersion, InstalledMetadataPath('package-info.ini'));
  SetIniString('Package', 'required_runtime_version', '{#RequiredRuntimeVersion}', InstalledMetadataPath('package-info.ini'));
  SetIniString('Package', 'base_package_version', BaseVersion, InstalledMetadataPath('package-info.ini'));
  SetIniString('Install', 'schema_version', '1', InstalledMetadataPath('install-instance.ini'));
  SetIniString('Install', 'instance_id', PathInstanceId(ExpandConstant('{app}')), InstalledMetadataPath('install-instance.ini'));
  SetIniString('Install', 'app_version', '{#MyAppVersion}', InstalledMetadataPath('install-instance.ini'));
  SetIniString('Install', 'runtime_version', RuntimeVersion, InstalledMetadataPath('install-instance.ini'));
  SetIniString('Install', 'base_package_version', BaseVersion, InstalledMetadataPath('install-instance.ini'));
  SetIniString('Install', 'model_bundle_version', BaseVersion,
    InstalledMetadataPath('install-instance.ini'));
end;

procedure WriteExtensionInstallState();
var
  ExtensionVersion: String;
begin
  ExtensionVersion := ReadExtensionVersionAt(InstanceExtensionRoot());
  if ExtensionVersion = '' then
    SetIniString('Install', 'model_export_installed', 'false',
      InstalledMetadataPath('install-instance.ini'))
  else
    SetIniString('Install', 'model_export_installed', 'true',
      InstalledMetadataPath('install-instance.ini'));
  SetIniString('Install', 'model_export_version', ExtensionVersion,
    InstalledMetadataPath('install-instance.ini'));
end;

function PreservedExtensionPath(): String;
begin
  Result := BackupPath('preserved-model-export-runtime');
end;

function PreserveExtensionForBaseInstall(): Boolean;
var
  Source, Destination: String;
begin
  Source := InstanceExtensionRoot();
  Destination := PreservedExtensionPath();
  if not DirExists(Source) then
  begin
    Result := True;
    exit;
  end;
  if DirExists(Destination) then
    DelTree(Destination, True, True, True);
  ForceDirectories(ExtractFileDir(Destination));
  Result := RenameFile(Source, Destination);
  if Result then
    ExtensionPreserved := True;
end;

function RestorePreservedExtension(): Boolean;
var
  Source, Destination: String;
begin
  Result := True;
  if not ExtensionPreserved then
    exit;
  Source := PreservedExtensionPath();
  Destination := InstanceExtensionRoot();
  if not DirExists(Source) then
  begin
    Result := False;
    exit;
  end;
  if DirExists(Destination) then
    DelTree(Destination, True, True, True);
  ForceDirectories(ExtractFileDir(Destination));
  Result := RenameFile(Source, Destination);
end;

function CommitMainInstall(): Boolean;
begin
  UpdateCommitStarted := True;
  Result := BackupExisting('YOLOTool.exe') and
    BackupExisting('app_assets') and
    BackupLegacyMetadata();
  if Result and ShouldInstallBase() then
    Result := PreserveExtensionForBaseInstall() and
      BackupExisting('_internal') and
      MergeModels()
  else if Result then
    Result := BackupProgramMetadata() and MigrateLegacyBaseMetadata();
  if Result then
    Result := MoveStaged(ProgramStagePath('YOLOTool.exe'), 'YOLOTool.exe');
  if Result and ShouldInstallBase() then
    Result := MoveStaged(BaseStagePath('_internal'), '_internal') and
      RestorePreservedExtension();
  if Result then
    Result := MoveStaged(ProgramStagePath('app-version.txt'),
        MetadataRelativePath('app-version.txt')) and
      MoveStaged(ProgramStagePath('release-manifest.json'),
        MetadataRelativePath('release-manifest.json'));
  if Result and ShouldInstallBase() then
    Result :=
      MoveStaged(BaseStagePath('runtime-manifest.json'),
        MetadataRelativePath('runtime-manifest.json')) and
      MoveStaged(BaseStagePath('base-package-manifest.json'),
        MetadataRelativePath('base-package-manifest.json')) and
      MoveStaged(BaseStagePath('managed-models.json'),
        MetadataRelativePath('managed-models.json'));
  if Result then
    Result := PrepareRootModel();
  if Result then
    WriteInstallState();
end;

procedure RestoreMainInstall();
begin
  if RollbackPerformed then
    exit;
  RollbackPerformed := True;
  RestoreExisting('YOLOTool.exe');
  RestoreExisting('app_assets');
  if ShouldInstallBase() then
  begin
    if ExtensionPreserved and DirExists(InstanceExtensionRoot()) then
    begin
      if DirExists(PreservedExtensionPath()) then
        DelTree(PreservedExtensionPath(), True, True, True);
      ForceDirectories(ExtractFileDir(PreservedExtensionPath()));
      RenameFile(InstanceExtensionRoot(), PreservedExtensionPath());
    end;
    RestoreMergedModels();
    RestoreExisting('_internal');
    RestorePreservedExtension();
  end
  else
  begin
    RestoreExisting(MetadataRelativePath('app-version.txt'));
    RestoreExisting(MetadataRelativePath('release-manifest.json'));
    RestoreExisting(MetadataRelativePath('package-info.ini'));
    RestoreExisting(MetadataRelativePath('install-instance.ini'));
    RestoreExisting(MetadataRelativePath('runtime-manifest.json'));
    RestoreExisting(MetadataRelativePath('base-package-manifest.json'));
    RestoreExisting(MetadataRelativePath('managed-models.json'));
  end;
  if RootModelTouched then
    RestoreExisting('yolo26n.pt');
  RestoreExisting('app-version.txt');
  RestoreExisting('release-manifest.json');
  RestoreExisting('runtime-manifest.json');
  RestoreExisting('runtime-version.txt');
  RestoreExisting('base-package-manifest.json');
  RestoreExisting('managed-models.json');
  RestoreExisting('package-info.ini');
  RestoreExisting('install-instance.ini');
end;

procedure CleanupTransaction();
begin
  if not TransactionInitialized then
    exit;
  DelTree(AddBackslash(TransactionAppDir) + '.install-staging', True, True, True);
  DelTree(AddBackslash(TransactionAppDir) + '.install-backup', True, True, True);
end;

function RunAppCommand(const Arguments: String; var ExitCode: Integer): Boolean;
begin
  Result := Exec(ExpandConstant('{app}\{#MyAppExeName}'), Arguments,
    ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, ExitCode);
end;

procedure RegisterExtraCloseApplicationsResources();
begin
  if FileExists(ExpandConstant('{app}\{#MyAppExeName}')) then
    RegisterExtraCloseApplicationsResource(
      True, ExpandConstant('{app}\{#MyAppExeName}'));
end;

function ShouldMigrateLegacyExtension(): Boolean;
begin
  Result := ExistingInstall and
    not DirExists(InstanceExtensionRoot()) and
    (DirExists(LegacyInstanceExtensionRoot()) or
      DirExists(ExpandConstant('{localappdata}\YOLOTool\extensions')));
end;

procedure InstallOptionalExtension();
var
  ExitCode: Integer;
begin
  if ShouldMigrateLegacyExtension() then
    if not RunAppCommand('--migrate-legacy-extension', ExitCode) or (ExitCode <> 0) then
      MsgBox('旧版模型转换附加环境迁移失败，程序仍可正常使用。', mbError, MB_OK);
  if ExtensionCheck.Checked then
    if not RunAppCommand('--install-model-export-package package="' +
      ExtensionArchivePath + '"', ExitCode) or (ExitCode <> 0) then
      MsgBox('模型转换附加环境安装失败，程序和基础环境已经安装完成。', mbError, MB_OK);
end;

function MainInstallSucceeded(): Boolean;
begin
  Result := UpdateCommitted;
end;

function InstanceUninstallKey(): String;
begin
  if IsLegacyInstallPath(ExpandConstant('{app}')) then
    Result := '{#LegacyUninstallKey}'
  else
    Result := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\' +
      'YOLOTool_' + PathInstanceId(ExpandConstant('{app}'));
end;

procedure RemoveUninstallRegistration();
var
  Key: String;
begin
  Key := InstanceUninstallKey();
  RegDeleteKeyIncludingSubkeys(HKLM64, Key);
  RegDeleteKeyIncludingSubkeys(HKLM32, Key);
  RegDeleteKeyIncludingSubkeys(HKCU64, Key);
  RegDeleteKeyIncludingSubkeys(HKCU32, Key);
end;

function WriteUninstallRegistration(): Boolean;
var
  Key, Uninstaller, DisplayName: String;
  RootKey: Integer;
begin
  Key := InstanceUninstallKey();
  Uninstaller := ExpandConstant('{app}\uninstall.exe');
  DisplayName := GetShortcutName('') + ' {#MyAppVersion}';
  RemoveUninstallRegistration();
  if IsAdminInstallMode() then
    RootKey := HKLM64
  else
    RootKey := HKCU64;
  Result :=
    RegWriteStringValue(RootKey, Key, 'DisplayName', DisplayName) and
    RegWriteStringValue(RootKey, Key, 'DisplayVersion', '{#MyAppVersion}') and
    RegWriteStringValue(RootKey, Key, 'Publisher', '{#MyAppPublisher}') and
    RegWriteStringValue(RootKey, Key, 'InstallLocation', ExpandConstant('{app}')) and
    RegWriteStringValue(RootKey, Key, 'DisplayIcon',
      ExpandConstant('{app}\{#MyAppExeName}')) and
    RegWriteStringValue(RootKey, Key, 'UninstallString', '"' + Uninstaller + '"') and
    RegWriteStringValue(RootKey, Key, 'QuietUninstallString',
      '"' + Uninstaller + '" /VERYSILENT /SUPPRESSMSGBOXES') and
    RegWriteDWordValue(RootKey, Key, 'NoModify', 1) and
    RegWriteDWordValue(RootKey, Key, 'NoRepair', 1);
end;

function RenameUninstallerFiles(): Boolean;
var
  OldExe, OldDat, NewExe, NewDat: String;
begin
  OldExe := ExpandConstant('{uninstallexe}');
  OldDat := ChangeFileExt(OldExe, '.dat');
  NewExe := ExpandConstant('{app}\uninstall.exe');
  NewDat := ChangeFileExt(NewExe, '.dat');
  if CompareText(OldExe, NewExe) = 0 then
  begin
    Result := FileExists(NewExe) and FileExists(NewDat);
    exit;
  end;
  if FileExists(NewExe) and not DeleteFile(NewExe) then
  begin
    Result := False;
    exit;
  end;
  if FileExists(NewDat) and not DeleteFile(NewDat) then
  begin
    Result := False;
    exit;
  end;
  Result := RenameFile(OldDat, NewDat) and RenameFile(OldExe, NewExe);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  FreeBytes, TotalBytes, RequiredBytes: Int64;
begin
  Result := '';
  TransactionAppDir := RemoveBackslashUnlessRoot(ExpandFileName(WizardDirValue));
  TransactionInitialized := True;
  if DirExists(AddBackslash(TransactionAppDir) + '.install-staging') or
    DirExists(AddBackslash(TransactionAppDir) + '.install-backup') then
  begin
    Result := '检测到上一次安装留下的临时目录，请确认旧版本可启动后删除临时目录再重试。';
    exit;
  end;
  if ShouldInstallBase() then
  begin
    if not IsValidBaseArchive() then
    begin
      Result := '本体环境和模型包缺失、名称不匹配或文件大小不正确。';
      exit;
    end;
    if not BaseArchiveHashVerified then
    begin
      BeginArchiveVerification('正在验证本体环境包，请稍候...');
      BaseArchiveHashVerified := VerifyArchiveHash(BaseArchivePath,
        '{#BasePackageHash}');
      EndArchiveVerification();
    end;
    if not BaseArchiveHashVerified then
    begin
      Result := '本体环境和模型包 SHA-256 校验失败。';
      exit;
    end;
    RequiredBytes := StrToInt64Def('{#BaseUnpackedSize}', 0) + 536870912;
    if GetSpaceOnDisk64(ExtractFileDrive(TransactionAppDir), FreeBytes, TotalBytes) and
      (FreeBytes < RequiredBytes) then
    begin
      Result := '安装磁盘空间不足，基础环境解压至少需要 ' +
        IntToStr(RequiredBytes div 1048576) + ' MB 可用空间。';
      exit;
    end;
  end;
  if ExtensionCheck.Checked then
  begin
    if not IsValidExtensionArchive() then
    begin
      Result := '模型转换附加包缺失、名称不匹配或文件大小不正确。';
      exit;
    end;
    if not ExtensionArchiveHashVerified then
    begin
      BeginArchiveVerification('正在验证模型转换附加包，请稍候...');
      ExtensionArchiveHashVerified := VerifyArchiveHash(ExtensionArchivePath,
        '{#ExtensionPackageHash}');
      EndArchiveVerification();
    end;
    if not ExtensionArchiveHashVerified then
      Result := '模型转换附加包 SHA-256 校验失败。';
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ExitCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    WizardForm.StatusLabel.Caption := '正在完成安装，请稍候...';
    WizardForm.FilenameLabel.Caption := '正在提交程序文件并执行运行环境自检...';
    WizardForm.ProgressGauge.Style := npbstNormal;
    WizardForm.ProgressGauge.Position := WizardForm.ProgressGauge.Max;
    WizardForm.ProgressGauge.Visible := True;
    WizardForm.Update;
    if not CommitMainInstall() then
    begin
      MsgBox('安装文件切换失败，正在恢复旧版本。', mbError, MB_OK);
      RestoreMainInstall();
      Abort;
    end;
    if ShouldInstallBase() then
    begin
      WizardForm.FilenameLabel.Caption := '正在检查新程序运行环境...';
      WizardForm.Update;
      if not RunAppCommand('--runtime-probe', ExitCode) or (ExitCode <> 0) then
      begin
        MsgBox('警告：新程序运行环境版本不一致或自检未通过。' + #13#10 +
          '安装将继续，但部分功能可能无法使用。', mbInformation, MB_OK);
        WizardForm.FilenameLabel.Caption :=
          '运行环境版本不一致或自检未通过，已继续安装；部分功能可能无法使用。';
        WizardForm.Update;
      end;
    end
    else
    begin
      if ExistingInstall and BaseIsRequired then
      begin
        MsgBox('警告：当前基础环境与新程序不匹配或不完整。' + #13#10 +
          '本次将继续使用旧环境，部分功能可能无法使用。',
          mbInformation, MB_OK);
        WizardForm.FilenameLabel.Caption :=
          '已保留旧运行环境；版本不匹配或环境不完整，部分功能可能无法使用。';
      end
      else
        WizardForm.FilenameLabel.Caption := '已保留当前运行环境，跳过环境版本自检。';
      WizardForm.Update;
    end;
    WizardForm.FilenameLabel.Caption := '正在登记安装实例...';
    WizardForm.Update;
    if not RenameUninstallerFiles() then
    begin
      MsgBox('无法重命名卸载程序文件，正在恢复旧版本。', mbError, MB_OK);
      RestoreMainInstall();
      Abort;
    end;
    if not WriteUninstallRegistration() then
    begin
      MsgBox('无法创建当前安装实例的卸载登记，正在恢复旧版本。', mbError, MB_OK);
      RestoreMainInstall();
      Abort;
    end;
    UpdateCommitted := True;
    InstallOptionalExtension();
    WriteExtensionInstallState();
    RegWriteStringValue(HKCU, 'Software\YOLOTool\Installer',
      'LastInstallPath', ExpandConstant('{app}'));
    CleanupTransaction();
  end;
end;

procedure DeinitializeSetup();
begin
  if not WizardInitialized then
    exit;
  if UpdateCommitStarted and not UpdateCommitted then
    RestoreMainInstall();
  if TransactionInitialized and not UpdateCommitted then
    CleanupTransaction();
end;

function InitializeUninstall(): Boolean;
begin
  if UninstallSilent() then
    Result := True
  else
    Result := MsgBox('卸载将删除程序、基础环境、受管官方模型和当前实例的附加环境。' + #13#10 +
      '项目设置、用户模型、images、labels 和 result 将保留。是否继续？',
      mbConfirmation, MB_YESNO) = IDYES;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ExitCode: Integer;
begin
  if CurUninstallStep = usUninstall then
  begin
    RunAppCommand('--remove-managed-models', ExitCode);
    DelTree(InstanceExtensionRoot(), True, True, True);
  end
  else if CurUninstallStep = usPostUninstall then
    RemoveUninstallRegistration();
end;
