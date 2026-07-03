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

$SourceModelsDir = Join-Path $Root "data/models"
if (Test-Path -LiteralPath $SourceModelsDir) {
    Get-ChildItem -LiteralPath $SourceModelsDir -Filter *.pt -File | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $AppDir "data/models" $_.Name) -Force
    }
}

$RootModelPath = Join-Path $Root "yolo26n.pt"
if (Test-Path -LiteralPath $RootModelPath) {
    Copy-Item -LiteralPath $RootModelPath -Destination (Join-Path $AppDir "yolo26n.pt") -Force
}

Write-Host "Mode: $Mode"
Write-Host "Built: $AppDir"
Write-Host "Project settings will be created at: $AppDir/data/runtime/settings.json"
