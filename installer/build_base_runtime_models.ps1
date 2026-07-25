param(
    [switch]$Clean,
    [string]$Version = "",
    [string]$RuntimeVersion = ""
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

if ([string]::IsNullOrWhiteSpace($Version)) {
    $Version = (Get-Content -LiteralPath (Join-Path $PSScriptRoot "base-runtime-models-version.txt") -Raw).Trim()
}
if ([string]::IsNullOrWhiteSpace($RuntimeVersion)) {
    $RuntimeVersion = (Get-Content -LiteralPath (Join-Path $PSScriptRoot "runtime-version.txt") -Raw).Trim()
}

$AppRoot = Join-Path $Root "dist\YOLOTool"
$StagingRoot = Join-Path $Root "dist\packages\BaseRuntimeModels"
$OutputDir = Join-Path $PSScriptRoot "output"
$OutputPath = Join-Path $OutputDir "YOLOTool_BaseEnv_${Version}.7z"
if (-not (Test-Path -LiteralPath (Join-Path $AppRoot "_internal"))) {
    throw "Frozen release output is missing. Run installer\build_windows.ps1 first."
}
if ($Clean) {
    Remove-Item -LiteralPath $StagingRoot -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $OutputPath -Force -ErrorAction SilentlyContinue
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$ForceArgs = @()
if ($Clean) {
    $ForceArgs += "--force"
}
pixi run -e release-base python -m src.devtools.base_runtime_package `
    --app-root $AppRoot `
    --staging-root $StagingRoot `
    --output-dir $OutputDir `
    --version $Version `
    --runtime-version $RuntimeVersion @ForceArgs
if ($LASTEXITCODE -ne 0) {
    throw "Base runtime and models archive build failed with exit code $LASTEXITCODE"
}

Write-Host "Built base runtime and models archive: $OutputPath"
