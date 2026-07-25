param(
    [ValidateSet("release", "dev")]
    [string]$Mode = "release",
    [switch]$Clean,
    [switch]$ProgramOnly,
    [ValidateSet("Program", "Full", "AppUpdate", "RuntimeFull")]
    [string]$PackageType = "Program",
    [string]$RuntimeVersion = "",
    [string]$RequiredRuntimeVersion = ""
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root
if ($PackageType -ne "Program") {
    Write-Warning "PackageType '$PackageType' is deprecated and now builds the Program package."
    $PackageType = "Program"
}
$PreviousPythonWarnings = $env:PYTHONWARNINGS
$env:PYTHONWARNINGS = "ignore::DeprecationWarning"
$PreviousBuildMode = $env:YOLO_TOOL_BUILD_MODE
$env:YOLO_TOOL_BUILD_MODE = $Mode
$PreviousProgramOnly = $env:YOLO_TOOL_PROGRAM_ONLY
$env:YOLO_TOOL_PROGRAM_ONLY = if ($ProgramOnly) { "1" } else { "0" }

$AppName = if ($Mode -eq "dev") {
    "YOLOTool-dev"
} else {
    "YOLOTool"
}
$BuildName = if ($ProgramOnly) { "$AppName-Program" } else { $AppName }
$BuildPath = Join-Path $Root "build\$BuildName"
$FullAppDir = Join-Path $Root "dist\$AppName"
$ProgramAppDir = Join-Path $Root "dist\$BuildName"
$OutputAppDir = if ($ProgramOnly) { $ProgramAppDir } else { $FullAppDir }
$OneFileOutput = if ($ProgramOnly) { Join-Path $Root "dist\$AppName.exe" } else { "" }

if ($Clean) {
    Remove-Item -LiteralPath $BuildPath -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $OutputAppDir -Recurse -Force -ErrorAction SilentlyContinue
}
if ($ProgramOnly) {
    Remove-Item -LiteralPath $OneFileOutput -Force -ErrorAction SilentlyContinue
}

try {
    pixi run -e release-base pyinstaller --noconfirm --log-level=WARN `
        --workpath "build\$BuildName" `
        --distpath "dist" `
        "installer/YOLOTool.spec"

    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE"
    }
}
finally {
    $env:PYTHONWARNINGS = $PreviousPythonWarnings
    $env:YOLO_TOOL_BUILD_MODE = $PreviousBuildMode
    $env:YOLO_TOOL_PROGRAM_ONLY = $PreviousProgramOnly
}

if ($ProgramOnly) {
    $AppDir = $ProgramAppDir
    $ExeName = "$AppName.exe"
    $ProgramOnlyCandidates = @(
        Get-ChildItem -LiteralPath $BuildPath -Filter $ExeName -File -Recurse -ErrorAction SilentlyContinue
    )
    if (Test-Path -LiteralPath $OneFileOutput) {
        $ProgramOnlyCandidates += Get-Item -LiteralPath $OneFileOutput
    }
    if ($ProgramOnlyCandidates.Count -ne 1) {
        $Found = if ($ProgramOnlyCandidates.Count -eq 0) {
            "none"
        } else {
            ($ProgramOnlyCandidates | ForEach-Object { $_.FullName }) -join "; "
        }
        throw "Expected exactly one program-only EXE under $BuildPath; found $($ProgramOnlyCandidates.Count): $Found"
    }
    Remove-Item -LiteralPath $AppDir -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Force -Path $AppDir | Out-Null
    Copy-Item -LiteralPath $ProgramOnlyCandidates[0].FullName -Destination (Join-Path $AppDir $ExeName) -Force
    Remove-Item -LiteralPath $OneFileOutput -Force -ErrorAction SilentlyContinue
    if (Test-Path -LiteralPath (Join-Path $AppDir "_internal")) {
        throw "Program-only output unexpectedly contains _internal: $AppDir"
    }
    $RuntimeSettingsPath = ""
    $RuntimeAppStatePath = ""
} else {
    $AppDir = $FullAppDir
    $ExeName = "$AppName.exe"
    New-Item -ItemType Directory -Force -Path (Join-Path $AppDir "data/runtime") | Out-Null
    $TargetModelsDir = Join-Path $AppDir "data/models"
    New-Item -ItemType Directory -Force -Path $TargetModelsDir | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $AppDir "images") | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $AppDir "labels") | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $AppDir "result") | Out-Null
    Remove-Item -LiteralPath (Join-Path $AppDir "_internal/src/assets") -Recurse -Force -ErrorAction SilentlyContinue
    $RuntimeSettingsPath = Join-Path $AppDir "data/runtime/settings.json"
    $RuntimeAppStatePath = Join-Path $AppDir "data/runtime/app_state.json"

    $SourceModelsDir = Join-Path $Root "data/models"
    $BaseModelNames = @("yolo11s.pt", "yolo26n.pt", "yolov8n.pt")
    $SourceModelFiles = @()
    if (Test-Path -LiteralPath $SourceModelsDir) {
        foreach ($ModelName in $BaseModelNames) {
            $ModelFile = Get-Item -LiteralPath (Join-Path $SourceModelsDir $ModelName) -ErrorAction SilentlyContinue
            if ($ModelFile) {
                $SourceModelFiles += $ModelFile
                Copy-Item -LiteralPath $ModelFile.FullName -Destination (Join-Path $TargetModelsDir $ModelName) -Force
            }
        }
    }

@"
from __future__ import annotations

import json
import sys
from pathlib import Path

from src.services.settings import build_default_settings, save_last_project_root

app_dir = Path(sys.argv[1]).resolve()
settings_path = app_dir / "data" / "runtime" / "settings.json"
settings_path.parent.mkdir(parents=True, exist_ok=True)
settings = build_default_settings(app_dir)
settings_path.write_text(
    json.dumps(settings, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
save_last_project_root(app_dir, app_dir / "data" / "runtime" / "app_state.json")
"@ | pixi run -e release-base python - $AppDir

if ($LASTEXITCODE -ne 0) {
    throw "Failed to generate packaged runtime settings files"
}

if (-not (Test-Path -LiteralPath $RuntimeSettingsPath)) {
    throw "Build output is missing runtime settings file: data/runtime/settings.json"
}

if (-not (Test-Path -LiteralPath $RuntimeAppStatePath)) {
    throw "Build output is missing app state file: data/runtime/app_state.json"
}

    $MissingModels = @()
    foreach ($ModelName in $BaseModelNames) {
        if (-not (Test-Path -LiteralPath (Join-Path $TargetModelsDir $ModelName))) {
            $MissingModels += $ModelName
        }
    }
    if ($MissingModels.Count -gt 0) {
        throw "Build output is missing required model files under data/models: $($MissingModels -join ', ')"
    }
}

$AppVersion = (& pixi run -e release-base python -c "from src import APP_VERSION; print(APP_VERSION)" | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($AppVersion)) {
    throw "Failed to read application version"
}

if ([string]::IsNullOrWhiteSpace($RuntimeVersion)) {
    $RuntimeVersion = (Get-Content -LiteralPath (Join-Path $PSScriptRoot "runtime-version.txt") -Raw).Trim()
}
if ([string]::IsNullOrWhiteSpace($RequiredRuntimeVersion)) {
    $RequiredRuntimeVersion = $RuntimeVersion
}
$StagingRoot = Join-Path $Root "dist/packages/$PackageType"
$PackageArgs = @(
    "-m", "src.devtools.release_package",
    "--app-root", $AppDir,
    "--output-root", $StagingRoot,
    "--package-type", $PackageType,
    "--exe-name", $ExeName,
    "--app-version", $AppVersion,
    "--runtime-version", $RuntimeVersion,
    "--required-runtime-version", $RequiredRuntimeVersion
)
& pixi run -e release-base python @PackageArgs
if ($LASTEXITCODE -ne 0) {
    throw "Failed to build $PackageType package staging"
}

Write-Host "Mode: $Mode"
Write-Host "Built: $AppDir"
Write-Host "Package type: $PackageType"
Write-Host "Package staging: $StagingRoot"
Write-Host "Application version: $AppVersion"
Write-Host "Runtime version: $RuntimeVersion"
Write-Host "Packaged runtime settings: $RuntimeSettingsPath"
Write-Host "Packaged app state: $RuntimeAppStatePath"

