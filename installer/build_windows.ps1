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

$SpecPath = if ($Mode -eq "dev") {
    "installer/YOLOTool.dev.spec"
} else {
    "installer/YOLOTool.spec"
}

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
        $SpecPath

    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE"
    }
}
finally {
    $env:PYTHONWARNINGS = $PreviousPythonWarnings
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
    # Copy the full models directory contents into dist/data/models.
    Copy-Item -Path (Join-Path $SourceModelsDir "*") -Destination $TargetModelsDir -Recurse -Force
}

$RootModelPath = Join-Path $Root "yolo26n.pt"
if (Test-Path -LiteralPath $RootModelPath) {
    Copy-Item -LiteralPath $RootModelPath -Destination (Join-Path $AppDir "yolo26n.pt") -Force
}

Write-Host "Mode: $Mode"
Write-Host "Built: $AppDir"
Write-Host "Project settings will be created at: $AppDir/data/runtime/settings.json"
