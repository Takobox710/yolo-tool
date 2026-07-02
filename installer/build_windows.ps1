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
New-Item -ItemType Directory -Force -Path (Join-Path $AppDir "data/models") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $AppDir "images") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $AppDir "labels") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $AppDir "result") | Out-Null

$SourceModelsDir = Join-Path $Root "data/models"
if (Test-Path $SourceModelsDir) {
    Get-ChildItem -Path $SourceModelsDir -Filter *.pt -File | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $AppDir "data/models" $_.Name) -Force
    }
}

$RootModelPath = Join-Path $Root "yolo26n.pt"
if (Test-Path $RootModelPath) {
    Copy-Item -LiteralPath $RootModelPath -Destination (Join-Path $AppDir "yolo26n.pt") -Force
}

Write-Host "Mode: $Mode"
Write-Host "Built: $AppDir"
Write-Host "Project settings will be created at: $AppDir/data/runtime/settings.json"
