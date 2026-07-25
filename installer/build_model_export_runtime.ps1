param(
    [switch]$Clean,
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

if ([string]::IsNullOrWhiteSpace($Version)) {
    $Version = (Get-Content -LiteralPath (Join-Path $PSScriptRoot "model-export-runtime-version.txt") -Raw).Trim()
}

$StagingRoot = Join-Path $Root "dist\packages\ModelExportRuntime"
$OutputDir = Join-Path $PSScriptRoot "output"
$OutputPath = Join-Path $OutputDir "YOLOTool_ExtraEnv_${Version}.7z"
if ($Clean) {
    Remove-Item -LiteralPath $StagingRoot -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $OutputPath -Force -ErrorAction SilentlyContinue
    foreach ($LegacySuffix in @("exe", "zip")) {
        $LegacyPath = Join-Path $OutputDir "YOLOTool_ExtraEnv_${Version}.$LegacySuffix"
        Remove-Item -LiteralPath $LegacyPath -Force -ErrorAction SilentlyContinue
    }
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$ForceArgs = @()
if ($Clean) {
    $ForceArgs += "--force"
}
pixi run -e export-full python -m src.devtools.model_export_package `
    --staging-root $StagingRoot `
    --output-dir $OutputDir `
    --version $Version @ForceArgs
if ($LASTEXITCODE -ne 0) {
    throw "Model export archive build failed with exit code $LASTEXITCODE"
}

Write-Host "Built additive LZMA2 model export archive: $OutputPath"
