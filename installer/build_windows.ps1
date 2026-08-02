param(
    [ValidateSet("release", "dev")]
    [string]$Mode = "release",
    [switch]$Clean,
    [switch]$ProgramOnly,
    [ValidateSet("GPU", "CPU")]
    [string]$Variant = "GPU",
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
$PreviousBuildVariant = $env:YOLO_TOOL_BUILD_VARIANT
$env:YOLO_TOOL_BUILD_VARIANT = $Variant.ToLowerInvariant()

$RuntimeEnvironment = if ($Variant -eq "CPU") { "release-cpu" } else { "release-gpu" }

$AppName = if ($Mode -eq "dev") {
    "YOLOTool-dev"
} else {
    "YOLOTool"
}
$VariantRoot = if ($Variant -eq "CPU") {
    Join-Path $Root "dist\CPU"
} else {
    Join-Path $Root "dist"
}
$BuildName = if ($ProgramOnly) {
    if ($Variant -eq "CPU") { "$AppName-CPU-Program" } else { "$AppName-Program" }
} else {
    if ($Variant -eq "CPU") { "$AppName-CPU" } else { $AppName }
}
$BuildPath = Join-Path $Root "build\$BuildName"
$FullAppDir = Join-Path $VariantRoot $AppName
$ProgramAppDir = Join-Path $VariantRoot "$AppName-Program"
$OutputAppDir = if ($ProgramOnly) { $ProgramAppDir } else { $FullAppDir }
$OneFileOutput = if ($ProgramOnly) { Join-Path $VariantRoot "$AppName.exe" } else { "" }

if ($Clean) {
    Remove-Item -LiteralPath $BuildPath -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $OutputAppDir -Recurse -Force -ErrorAction SilentlyContinue
}
if ($ProgramOnly) {
    Remove-Item -LiteralPath $OneFileOutput -Force -ErrorAction SilentlyContinue
}

try {
    $PyInstallerTimer = [System.Diagnostics.Stopwatch]::StartNew()
    if ($ProgramOnly) {
        Write-Host "[程序构建] 正在使用 PyInstaller 构建仅程序版本..." -ForegroundColor Cyan
    } else {
        Write-Host "[程序构建] 正在使用 PyInstaller 构建完整冻结程序..." -ForegroundColor Cyan
    }
    pixi run -e $RuntimeEnvironment pyinstaller --noconfirm --log-level=WARN `
        --workpath "build\$BuildName" `
        --distpath $VariantRoot `
        "installer/YOLOTool.spec"

    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller 构建失败，退出码：$LASTEXITCODE"
    }
    $PyInstallerTimer.Stop()
    Write-Host "[程序构建] PyInstaller 阶段耗时：$($PyInstallerTimer.Elapsed.TotalSeconds.ToString('N2')) 秒" -ForegroundColor Green
    Write-Host "[程序构建] PyInstaller 构建完成。" -ForegroundColor Green
}
finally {
    $env:PYTHONWARNINGS = $PreviousPythonWarnings
    $env:YOLO_TOOL_BUILD_MODE = $PreviousBuildMode
    $env:YOLO_TOOL_PROGRAM_ONLY = $PreviousProgramOnly
    $env:YOLO_TOOL_BUILD_VARIANT = $PreviousBuildVariant
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
        throw "程序版本应在 $BuildPath 下找到唯一 EXE，实际找到 $($ProgramOnlyCandidates.Count) 个：$Found"
    }
    Remove-Item -LiteralPath $AppDir -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Force -Path $AppDir | Out-Null
    Copy-Item -LiteralPath $ProgramOnlyCandidates[0].FullName -Destination (Join-Path $AppDir $ExeName) -Force
    Remove-Item -LiteralPath $OneFileOutput -Force -ErrorAction SilentlyContinue
    if (Test-Path -LiteralPath (Join-Path $AppDir "_internal")) {
        throw "仅程序输出异常包含 _internal 目录：$AppDir"
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
    $BaseModelNames = @(
        "yolo11s.pt",
        "yolo26n.pt",
        "yolov8n.pt"
    )
    $BaseModelNames += if ($Variant -eq "CPU") {
        "sam2.1_hiera_tiny.pt"
    } else {
        "sam2.1_hiera_base_plus.pt"
    }
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

from src.services.settings import build_default_settings, save_last_project_root, settings_to_dict

app_dir = Path(sys.argv[1]).resolve()
settings_path = app_dir / "data" / "runtime" / "settings.json"
settings_path.parent.mkdir(parents=True, exist_ok=True)
settings = build_default_settings(app_dir)
settings_path.write_text(
    json.dumps(settings_to_dict(settings), ensure_ascii=False, indent=2),
    encoding="utf-8",
)
save_last_project_root(app_dir, app_dir / "data" / "runtime" / "app_state.json")
"@ | pixi run -e $RuntimeEnvironment python - $AppDir

if ($LASTEXITCODE -ne 0) {
    throw "生成打包后的运行时设置文件失败。"
}

if (-not (Test-Path -LiteralPath $RuntimeSettingsPath)) {
    throw "构建输出缺少运行时设置文件：data/runtime/settings.json"
}

if (-not (Test-Path -LiteralPath $RuntimeAppStatePath)) {
    throw "构建输出缺少应用状态文件：data/runtime/app_state.json"
}

    $MissingModels = @()
    foreach ($ModelName in $BaseModelNames) {
        if (-not (Test-Path -LiteralPath (Join-Path $TargetModelsDir $ModelName))) {
            $MissingModels += $ModelName
        }
    }
    if ($MissingModels.Count -gt 0) {
            throw "构建输出缺少 data/models 下的基础模型：$($MissingModels -join ', ')"
    }
}

if ($Variant -eq "CPU") {
    $GuardArgs = @("-m", "src.devtools.cpu_package_guard")
    if (-not $ProgramOnly) {
        $GuardArgs += "--runtime-root"
        $GuardArgs += Join-Path $AppDir "_internal"
    }
    & pixi run -e $RuntimeEnvironment python @GuardArgs
    if ($LASTEXITCODE -ne 0) {
        throw "CPU 打包安全检查失败，已拒绝继续生成 CPU 产物。"
    }
}

$AppVersion = (& pixi run -e $RuntimeEnvironment python -c "from src import APP_VERSION; print(APP_VERSION)" | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($AppVersion)) {
    throw "读取应用版本失败。"
}

if ([string]::IsNullOrWhiteSpace($RuntimeVersion)) {
    $RuntimeVersion = (Get-Content -LiteralPath (Join-Path $PSScriptRoot "runtime-version.txt") -Raw).Trim()
}
if ([string]::IsNullOrWhiteSpace($RequiredRuntimeVersion)) {
    $RequiredRuntimeVersion = $RuntimeVersion
}

if (-not $ProgramOnly) {
    # Keep a complete frozen build runnable before it is assembled into an
    # installer. The packaged layers still receive their full manifests later.
    $StandaloneReleaseManifest = @{
        schema_version = 2
        app_version = $AppVersion
        required_runtime_version = $RequiredRuntimeVersion
        variant = $Variant.ToLowerInvariant()
        app_files = @{
            $ExeName = (Get-FileHash -LiteralPath (Join-Path $AppDir $ExeName) -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    } | ConvertTo-Json -Depth 4
    $StandaloneRuntimeManifest = @{
        schema_version = 2
        runtime_version = $RuntimeVersion
        variant = $Variant.ToLowerInvariant()
        files = @{}
    } | ConvertTo-Json -Depth 4
    $Utf8NoBom = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText(
        (Join-Path $AppDir "release-manifest.json"),
        $StandaloneReleaseManifest + [Environment]::NewLine,
        $Utf8NoBom
    )
    [System.IO.File]::WriteAllText(
        (Join-Path $AppDir "runtime-manifest.json"),
        $StandaloneRuntimeManifest + [Environment]::NewLine,
        $Utf8NoBom
    )
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
    "--required-runtime-version", $RequiredRuntimeVersion,
    "--variant", $Variant.ToLowerInvariant()
)
$StagingTimer = [System.Diagnostics.Stopwatch]::StartNew()
& pixi run -e $RuntimeEnvironment python @PackageArgs
if ($LASTEXITCODE -ne 0) {
    throw "生成 $PackageType 包 staging 失败。"
}
$StagingTimer.Stop()
Write-Host "[程序构建] staging 阶段耗时：$($StagingTimer.Elapsed.TotalSeconds.ToString('N2')) 秒" -ForegroundColor Green

Write-Host "Mode: $Mode"
Write-Host "Built: $AppDir"
Write-Host "Package type: $PackageType"
Write-Host "Package staging: $StagingRoot"
Write-Host "Application version: $AppVersion"
Write-Host "Build variant: $Variant"
Write-Host "Runtime version: $RuntimeVersion"
Write-Host "Packaged runtime settings: $RuntimeSettingsPath"
Write-Host "Packaged app state: $RuntimeAppStatePath"

