param(
    [switch]$Clean,
    [string]$Version = "",
    [string]$RuntimeVersion = "",
    [ValidateSet("GPU", "CPU")]
    [string]$Variant = "GPU",
    [switch]$SplitBaseArchive,
    [switch]$NoArchive
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

$VariantRoot = if ($Variant -eq "CPU") {
    Join-Path $Root "dist\CPU"
} else {
    Join-Path $Root "dist"
}
$AppRoot = Join-Path $VariantRoot "YOLOTool"
$StagingName = if ($Variant -eq "CPU") { "BaseRuntimeModels-CPU" } else { "BaseRuntimeModels" }
$StagingRoot = Join-Path $Root "dist\packages\$StagingName"
$OutputDir = Join-Path $PSScriptRoot "output"
$ArtifactPrefix = if ($Variant -eq "CPU") { "YOLOTool_CPU" } else { "YOLOTool" }
$ArchivePath = Join-Path $OutputDir "${ArtifactPrefix}_BaseEnv_${Version}.7z"
$OutputPath = if ($SplitBaseArchive) { "${ArchivePath}.001" } else { $ArchivePath }
if (-not (Test-Path -LiteralPath (Join-Path $AppRoot "_internal"))) {
    throw "缺少冻结程序输出，请先运行 installer\build_windows.ps1。"
}
if ($Clean) {
    Remove-Item -LiteralPath $StagingRoot -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $ArchivePath -Force -ErrorAction SilentlyContinue
    Get-ChildItem -LiteralPath $OutputDir -Filter "${ArtifactPrefix}_BaseEnv_${Version}.7z.???" -File -ErrorAction SilentlyContinue |
        Remove-Item -Force
}
if ($NoArchive) {
    Get-ChildItem -LiteralPath $OutputDir -Filter "${ArtifactPrefix}_BaseEnv_${Version}.7z*" -File -ErrorAction SilentlyContinue |
        Remove-Item -Force
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$PackageArgs = @(
    "-m", "src.devtools.base_runtime_package",
    "--app-root", $AppRoot,
    "--staging-root", $StagingRoot,
    "--output-dir", $OutputDir,
    "--version", $Version,
    "--runtime-version", $RuntimeVersion,
    "--variant", $Variant.ToLowerInvariant()
)
if ($SplitBaseArchive) {
    $PackageArgs += "--split"
}
if ($NoArchive) {
    if ($SplitBaseArchive) {
        throw "-NoArchive 不能与 -SplitBaseArchive 同时使用。"
    }
    $PackageArgs += "--staging-only"
}
& pixi run -e $(if ($Variant -eq "CPU") { "release-cpu" } else { "release-base" }) python @PackageArgs
if ($LASTEXITCODE -ne 0) {
    throw "基础环境和模型归档构建失败，退出码：$LASTEXITCODE"
}

if ($NoArchive) {
    if (-not (Test-Path -LiteralPath (Join-Path $StagingRoot "base-package-manifest.json"))) {
        throw "基础运行时 staging 未生成清单：$StagingRoot"
    }
    Write-Host "基础运行时 staging 已生成：$StagingRoot" -ForegroundColor Green
    exit 0
}
if (-not (Test-Path -LiteralPath $OutputPath)) {
    throw "基础环境归档未生成：$OutputPath"
}

Write-Host "基础环境和模型归档已生成：$OutputPath" -ForegroundColor Green
