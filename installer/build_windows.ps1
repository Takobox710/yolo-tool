param(
    [ValidateSet("release", "dev")]
    [string]$Mode = "release",
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root
$PreviousPythonWarnings = $env:PYTHONWARNINGS
$env:PYTHONWARNINGS = "ignore::DeprecationWarning"
$PreviousBuildMode = $env:YOLO_TOOL_BUILD_MODE
$env:YOLO_TOOL_BUILD_MODE = $Mode

$AppName = if ($Mode -eq "dev") {
    "YOLOTool-dev"
} else {
    "YOLOTool"
}

if ($Clean) {
    Remove-Item -LiteralPath (Join-Path $Root "build\$AppName") -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath (Join-Path $Root "dist\$AppName") -Recurse -Force -ErrorAction SilentlyContinue
}

try {
    pixi run pyinstaller --noconfirm --log-level=WARN `
        --workpath "build\$AppName" `
        --distpath "dist" `
        "installer/YOLOTool.spec"

    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE"
    }
}
finally {
    $env:PYTHONWARNINGS = $PreviousPythonWarnings
    $env:YOLO_TOOL_BUILD_MODE = $PreviousBuildMode
}

$AppDir = Join-Path $Root "dist/$AppName"
New-Item -ItemType Directory -Force -Path (Join-Path $AppDir "data/runtime") | Out-Null
$TargetModelsDir = Join-Path $AppDir "data/models"
New-Item -ItemType Directory -Force -Path $TargetModelsDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $AppDir "images") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $AppDir "labels") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $AppDir "result") | Out-Null
$RuntimeSettingsPath = Join-Path $AppDir "data/runtime/settings.json"
$RuntimeAppStatePath = Join-Path $AppDir "data/runtime/app_state.json"

$SourceModelsDir = Join-Path $Root "data/models"
$SourceModelFiles = @()
if (Test-Path -LiteralPath $SourceModelsDir) {
    $SourceModelFiles = @(Get-ChildItem -LiteralPath $SourceModelsDir -Filter *.pt -File)
    foreach ($ModelFile in $SourceModelFiles) {
        $TargetModelPath = Join-Path $TargetModelsDir $ModelFile.Name
        Copy-Item -LiteralPath $ModelFile.FullName -Destination $TargetModelPath -Force
    }
}

$RootModelPath = Join-Path $Root "yolo26n.pt"
$TargetRootModelPath = Join-Path $AppDir "yolo26n.pt"
if (-not (Test-Path -LiteralPath $RootModelPath)) {
    throw "Required root model file not found: $RootModelPath"
}
Copy-Item -LiteralPath $RootModelPath -Destination $TargetRootModelPath -Force

if (-not (Test-Path -LiteralPath $TargetRootModelPath)) {
    throw "Build output is missing root model file: yolo26n.pt"
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
"@ | pixi run python - $AppDir

if ($LASTEXITCODE -ne 0) {
    throw "Failed to generate packaged runtime settings files"
}

if (-not (Test-Path -LiteralPath $RuntimeSettingsPath)) {
    throw "Build output is missing runtime settings file: data/runtime/settings.json"
}

if (-not (Test-Path -LiteralPath $RuntimeAppStatePath)) {
    throw "Build output is missing app state file: data/runtime/app_state.json"
}

if ($SourceModelFiles.Count -gt 0) {
    $MissingModels = @()
    foreach ($ModelName in ($SourceModelFiles | ForEach-Object { $_.Name })) {
        $BuiltModelPath = Join-Path $TargetModelsDir $ModelName
        if (-not (Test-Path -LiteralPath $BuiltModelPath)) {
            $MissingModels += $ModelName
        }
    }

    if ($MissingModels.Count -gt 0) {
        throw "Build output is missing model files under data/models: $($MissingModels -join ', ')"
    }
}

Write-Host "Mode: $Mode"
Write-Host "Built: $AppDir"
Write-Host "Packaged runtime settings: $RuntimeSettingsPath"
Write-Host "Packaged app state: $RuntimeAppStatePath"

