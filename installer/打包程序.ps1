param(
    [switch]$Clean,
    [switch]$SkipBaseRuntimeModels,
    [switch]$SkipModelExportRuntime
)

$Arguments = @{
    Clean = $Clean
    BuildBaseRuntimeModels = -not $SkipBaseRuntimeModels
    BuildModelExportRuntime = -not $SkipModelExportRuntime
}
& (Join-Path $PSScriptRoot "package_windows.ps1") @Arguments
exit $LASTEXITCODE
