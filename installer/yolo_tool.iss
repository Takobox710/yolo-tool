#define MyAppName "YOLOTool"
#define MyAppVersion "1.2.1"
#define MyAppPublisher "Takobox"
#define MyAppExeName "YOLOTool.exe"
#define MyAppIdEscaped "{{AFD7B4C3-5B11-4F8D-8BA1-64D96FD3C4A1}"
#define MyAppIdValue "{AFD7B4C3-5B11-4F8D-8BA1-64D96FD3C4A1}"

[Setup]
AppId={#MyAppIdEscaped}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DisableDirPage=no
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=output
OutputBaseFilename={#MyAppName}_Setup_{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
SetupIconFile=..\src\assets\app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务:"; Flags: unchecked

[Dirs]
Name: "{app}\data\models"
Name: "{app}\data\runtime"
Name: "{app}\images"
Name: "{app}\labels"
Name: "{app}\result"

[Files]
; 应用核心文件 - 每次升级覆盖
Source: "..\dist\YOLOTool\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\YOLOTool\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\dist\YOLOTool\*.pt"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

; 默认模型与示例资源 - 每次升级覆盖
Source: "..\dist\YOLOTool\data\models\*"; DestDir: "{app}\data\models"; Flags: ignoreversion skipifsourcedoesntexist recursesubdirs createallsubdirs
Source: "..\dist\YOLOTool\images\*"; DestDir: "{app}\images"; Flags: ignoreversion skipifsourcedoesntexist recursesubdirs createallsubdirs
Source: "..\dist\YOLOTool\labels\*"; DestDir: "{app}\labels"; Flags: ignoreversion skipifsourcedoesntexist recursesubdirs createallsubdirs

; 运行时配置与训练结果默认保留用户现场，仅首次安装写入
Source: "..\dist\YOLOTool\data\runtime\settings.json"; DestDir: "{app}\data\runtime"; Flags: onlyifdoesntexist
Source: "..\dist\YOLOTool\data\runtime\app_state.json"; DestDir: "{app}\data\runtime"; Flags: onlyifdoesntexist
Source: "..\dist\YOLOTool\result\*"; DestDir: "{app}\result"; Flags: onlyifdoesntexist skipifsourcedoesntexist recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
function PreviousInstallExists(): Boolean;
var
  UninstallKey: string;
begin
  UninstallKey := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppIdValue}_is1';
  Result :=
    RegKeyExists(HKLM64, UninstallKey) or
    RegKeyExists(HKLM32, UninstallKey) or
    RegKeyExists(HKCU64, UninstallKey) or
    RegKeyExists(HKCU32, UninstallKey);
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if (CurPageID = wpSelectDir) and PreviousInstallExists() then
  begin
    WizardForm.DirEdit.ReadOnly := True;
    WizardForm.DirBrowseButton.Enabled := False;
  end;
end;
