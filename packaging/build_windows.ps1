param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

if ($Clean) {
    Remove-Item -LiteralPath (Join-Path $Root "build") -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath (Join-Path $Root "dist") -Recurse -Force -ErrorAction SilentlyContinue
}

pixi run pyinstaller --noconfirm --log-level=WARN "packaging/YOLOTool.spec"

$AppDir = Join-Path $Root "dist/YOLOTool"
New-Item -ItemType Directory -Force -Path (Join-Path $AppDir "data/runtime") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $AppDir "data/models") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $AppDir "images") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $AppDir "labels") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $AppDir "result") | Out-Null

Write-Host "Built: $AppDir"
Write-Host "Project settings will be created at: $AppDir/data/runtime/settings.json"
