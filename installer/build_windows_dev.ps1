param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")

& (Join-Path $Root "installer/build_windows.ps1") -Mode dev -Clean:$Clean
