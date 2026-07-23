param(
    [switch]$Clean,
    [ValidateSet("Full", "AppUpdate", "RuntimeFull")]
    [string]$PackageType = "Full",
    [string]$RuntimeVersion = "",
    [string]$RequiredRuntimeVersion = ""
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$InstallerScript = Join-Path $PSScriptRoot "yolo_tool.iss"
$InstallerOutputDir = Join-Path $PSScriptRoot "output"

function Write-Step {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Cyan
}

function Get-InnoSetupCompiler {
    $candidates = @()

    try {
        $registryPaths = @(
            "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1",
            "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1"
        )
        foreach ($registryPath in $registryPaths) {
            if (Test-Path -LiteralPath $registryPath) {
                $installLocation = (Get-ItemProperty -LiteralPath $registryPath -ErrorAction Stop).InstallLocation
                if ($installLocation) {
                    $candidates += (Join-Path $installLocation "ISCC.exe")
                }
            }
        }
    }
    catch {
        # Fall back to common installation paths below.
    }

    $candidates += @(
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe",
        "D:\ruanjian\Inno Setup 6\ISCC.exe"
    )

    foreach ($candidate in $candidates | Select-Object -Unique) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) {
            return $candidate
        }
    }

    return $null
}

Set-Location $Root

try {
    Write-Step "[1/3] Building with PyInstaller..."
    $buildArgs = @{
        Mode = "release"
        Clean = $Clean
        PackageType = $PackageType
        RuntimeVersion = $RuntimeVersion
        RequiredRuntimeVersion = $RequiredRuntimeVersion
    }
    & (Join-Path $PSScriptRoot "build_windows.ps1") @buildArgs
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build failed with exit code $LASTEXITCODE"
    }

    $isccPath = Get-InnoSetupCompiler
    if (-not $isccPath) {
        throw "ISCC.exe was not found. Please install Inno Setup 6 first."
    }

    Write-Step "[2/3] Building installer with Inno Setup..."
    New-Item -ItemType Directory -Force -Path $InstallerOutputDir | Out-Null
    if ([string]::IsNullOrWhiteSpace($RuntimeVersion)) {
        $RuntimeVersion = (Get-Content -LiteralPath (Join-Path $PSScriptRoot "runtime-version.txt") -Raw).Trim()
    }
    if ([string]::IsNullOrWhiteSpace($RequiredRuntimeVersion)) {
        $RequiredRuntimeVersion = $RuntimeVersion
    }
    $AppVersion = (& pixi run python -c "from src import APP_VERSION; print(APP_VERSION)" | Out-String).Trim()
    & $isccPath "/DPackageType=$PackageType" "/DMyAppVersion=$AppVersion" "/DRequiredRuntimeVersion=$RequiredRuntimeVersion" $InstallerScript
    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup build failed with exit code $LASTEXITCODE"
    }

    Write-Step "[3/3] Build finished"
    Write-Host "Portable app: $(Join-Path $Root 'dist\YOLOTool')" -ForegroundColor Green
    Write-Host "Installer output: $InstallerOutputDir" -ForegroundColor Green
}
catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
