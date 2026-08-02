param(
    [switch]$Clean,
    [string]$Version = "",
    [switch]$SplitArchive
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

if ([string]::IsNullOrWhiteSpace($Version)) {
    $Version = (Get-Content -LiteralPath (Join-Path $PSScriptRoot "model-export-runtime-version.txt") -Raw).Trim()
}

$StagingRoot = Join-Path $Root "dist\packages\ModelExportRuntime"
$BaseStagingRoot = Join-Path $Root "dist\packages\BaseRuntimeModels"
$OutputDir = Join-Path $PSScriptRoot "output"
$ArchivePath = Join-Path $OutputDir "YOLOTool_ExtraEnv_${Version}.7z"
$OutputPath = if ($SplitArchive) { "${ArchivePath}.001" } else { $ArchivePath }
if ($Clean) {
    Remove-Item -LiteralPath $StagingRoot -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $ArchivePath -Force -ErrorAction SilentlyContinue
    Get-ChildItem -LiteralPath $OutputDir -Filter "YOLOTool_ExtraEnv_${Version}.7z.???" -File -ErrorAction SilentlyContinue |
        Remove-Item -Force
    foreach ($LegacySuffix in @("exe", "zip")) {
        $LegacyPath = Join-Path $OutputDir "YOLOTool_ExtraEnv_${Version}.$LegacySuffix"
        Remove-Item -LiteralPath $LegacyPath -Force -ErrorAction SilentlyContinue
    }
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$PackageArgs = @(
    "-m", "src.devtools.model_export_package",
    "--staging-root", $StagingRoot,
    "--output-dir", $OutputDir,
    "--version", $Version
)
if (Test-Path -LiteralPath (Join-Path $BaseStagingRoot "base-package-manifest.json")) {
    $PackageArgs += @("--base-staging", $BaseStagingRoot)
}
if ($SplitArchive) {
    $PackageArgs += "--split"
}
& pixi run -e release-gpu python @PackageArgs
if ($LASTEXITCODE -ne 0) {
    throw "附加模型转换环境归档构建失败，退出码：$LASTEXITCODE"
}

if (-not (Test-Path -LiteralPath $OutputPath)) {
    throw "附加模型转换环境归档未生成：$OutputPath"
}

Write-Host "附加模型转换环境归档已生成：$OutputPath" -ForegroundColor Green
