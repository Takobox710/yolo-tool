param(
    [switch]$Clean,
    [switch]$BuildBaseRuntimeModels,
    [switch]$BuildModelExportRuntime,
    [switch]$SkipModelExportRuntime,
    [ValidateSet("Program", "Full", "AppUpdate", "RuntimeFull")]
    [string]$PackageType = "Program",
    [string]$RuntimeVersion = "",
    [string]$RequiredRuntimeVersion = ""
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$InstallerScript = Join-Path $PSScriptRoot "yolo_tool.iss"
$InstallerOutputDir = Join-Path $PSScriptRoot "output"

function Write-Step {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Cyan
}

function Get-InnoSetupCompiler {
    $candidates = [System.Collections.Generic.List[string]]@(
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe",
        "D:\ruanjian\Inno Setup 6\ISCC.exe"
    )
    $command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($command) {
        $candidates.Add($command.Source)
    }
    $uninstallRoots = @(
        "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*",
        "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*",
        "HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*"
    )
    Get-ItemProperty $uninstallRoots -ErrorAction SilentlyContinue |
        Where-Object { $_.DisplayName -like "Inno Setup version 6*" } |
        ForEach-Object {
            if ($_.InstallLocation) {
                $candidates.Add((Join-Path $_.InstallLocation "ISCC.exe"))
            }
        }
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }
    return $null
}

Set-Location $Root
try {
    if ($PackageType -ne "Program") {
        Write-Warning "PackageType '$PackageType' is deprecated and now maps to Program."
    }
    if ($SkipModelExportRuntime) {
        Write-Warning "SkipModelExportRuntime is deprecated; optional archives are no longer built unless requested."
        $BuildModelExportRuntime = $false
    }
    if ([string]::IsNullOrWhiteSpace($RuntimeVersion)) {
        $RuntimeVersion = (Get-Content -LiteralPath (Join-Path $PSScriptRoot "runtime-version.txt") -Raw).Trim()
    }
    if ([string]::IsNullOrWhiteSpace($RequiredRuntimeVersion)) {
        $RequiredRuntimeVersion = $RuntimeVersion
    }

    $BaseVersion = (Get-Content -LiteralPath (Join-Path $PSScriptRoot "base-runtime-models-version.txt") -Raw).Trim()
    $BaseArchive = Join-Path $InstallerOutputDir "YOLOTool_BaseEnv_${BaseVersion}.7z"
    $BaseAppRoot = Join-Path $Root "dist\YOLOTool"
    $BaseArchiveCurrent = $false
    if ($BuildBaseRuntimeModels -and -not $Clean -and
        (Test-Path -LiteralPath $BaseArchive) -and
        (Test-Path -LiteralPath (Join-Path $BaseAppRoot "_internal"))) {
        $BaseCacheCheck = & pixi run -e release-base python -m src.devtools.base_runtime_package `
            --app-root $BaseAppRoot `
            --staging-root (Join-Path $Root "dist\packages\BaseRuntimeModels") `
            --output-dir $InstallerOutputDir `
            --version $BaseVersion `
            --runtime-version $RuntimeVersion `
            --check-current
        if ($LASTEXITCODE -eq 0 -and (($BaseCacheCheck -join "").Trim() -eq "true")) {
            $BaseArchiveCurrent = $true
            Write-Step "Base runtime archive is unchanged; reusing cached archive."
        }
    }
    if (-not $BuildBaseRuntimeModels -and -not (Test-Path -LiteralPath $BaseArchive)) {
        throw "Required base archive is missing: $BaseArchive. Run the full packaging entry first."
    }

    $ProgramOnly = -not $BuildBaseRuntimeModels -or $BaseArchiveCurrent
    if ($ProgramOnly) {
        if ($BaseArchiveCurrent) {
            Write-Step "[1/5] Building program-only EXE and reusing runtime archives..."
        } else {
            Write-Step "[1/5] Building program-only EXE and Program staging..."
        }
    } else {
        Write-Step "[1/5] Building frozen application and Program staging..."
    }
    & (Join-Path $PSScriptRoot "build_windows.ps1") `
        -Mode release -Clean:$Clean -PackageType Program `
        -ProgramOnly:$ProgramOnly `
        -RuntimeVersion $RuntimeVersion -RequiredRuntimeVersion $RequiredRuntimeVersion
    if ($LASTEXITCODE -ne 0) {
        throw "Program build failed with exit code $LASTEXITCODE"
    }

    if ($BuildBaseRuntimeModels) {
        if ($BaseArchiveCurrent) {
            Write-Step "[2/5] Reusing unchanged base runtime and models archive..."
        } else {
            Write-Step "[2/5] Building base runtime and models archive..."
            & (Join-Path $PSScriptRoot "build_base_runtime_models.ps1") `
                -Clean:$Clean -RuntimeVersion $RuntimeVersion
            if ($LASTEXITCODE -ne 0) {
                throw "Base runtime and models build failed with exit code $LASTEXITCODE"
            }
        }
    }
    if ($BuildModelExportRuntime) {
        Write-Step "[3/5] Building optional model export archive..."
        & (Join-Path $PSScriptRoot "build_model_export_runtime.ps1") -Clean:$Clean
        if ($LASTEXITCODE -ne 0) {
            throw "Model export runtime build failed with exit code $LASTEXITCODE"
        }
    }

    if (-not (Test-Path -LiteralPath $BaseArchive)) {
        throw "Required base archive is missing: $BaseArchive. Re-run with -BuildBaseRuntimeModels."
    }
    $ExtensionVersion = (Get-Content -LiteralPath (Join-Path $PSScriptRoot "model-export-runtime-version.txt") -Raw).Trim()
    $ExtensionArchive = Join-Path $InstallerOutputDir "YOLOTool_ExtraEnv_${ExtensionVersion}.7z"
    $ProgramStaging = Join-Path $Root "dist\packages\Program"
    $CatalogPath = Join-Path $ProgramStaging "companion-catalog.json"
    $CatalogArgs = @(
        "-m", "src.devtools.companion_catalog",
        "--base", $BaseArchive,
        "--output", $CatalogPath
    )
    if (Test-Path -LiteralPath $ExtensionArchive) {
        $CatalogArgs += @("--extension", $ExtensionArchive)
    }
    & pixi run -e release-base python @CatalogArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to build companion package catalog"
    }
    $Catalog = Get-Content -LiteralPath $CatalogPath -Raw | ConvertFrom-Json
    if ($Catalog.base.runtime_version -ne $RequiredRuntimeVersion) {
        throw "Base package runtime '$($Catalog.base.runtime_version)' does not match required runtime '$RequiredRuntimeVersion'."
    }

    $isccPath = Get-InnoSetupCompiler
    if (-not $isccPath) {
        throw "ISCC.exe was not found. Install Inno Setup 6.4 or newer."
    }
    $AppVersion = (& pixi run -e release-base python -c "from src import APP_VERSION; print(APP_VERSION)" | Out-String).Trim()
    $InnoArgs = @(
        "/DMyAppVersion=$AppVersion",
        "/DRequiredRuntimeVersion=$RequiredRuntimeVersion",
        "/DBasePackageName=$($Catalog.base.filename)",
        "/DBasePackageHash=$($Catalog.base.sha256)",
        "/DBaseCompressedSize=$($Catalog.base.compressed_size)",
        "/DBasePackageVersion=$($Catalog.base.version)",
        "/DBaseRuntimeVersion=$($Catalog.base.runtime_version)",
        "/DBaseUnpackedSize=$($Catalog.base.uncompressed_size)"
    )
    if ($Catalog.model_export) {
        $InnoArgs += @(
            "/DExtensionPackageName=$($Catalog.model_export.filename)",
            "/DExtensionPackageHash=$($Catalog.model_export.sha256)",
            "/DExtensionCompressedSize=$($Catalog.model_export.compressed_size)",
            "/DExtensionPackageVersion=$($Catalog.model_export.version)"
        )
    }

    Write-Step "[4/5] Building unified Program Setup..."
    New-Item -ItemType Directory -Force -Path $InstallerOutputDir | Out-Null
    & $isccPath @InnoArgs $InstallerScript
    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup build failed with exit code $LASTEXITCODE"
    }

    Write-Step "[5/5] Build finished"
    Write-Host "Program Setup: $(Join-Path $InstallerOutputDir "YOLOTool_Setup_${AppVersion}.exe")" -ForegroundColor Green
    Write-Host "Base archive: $BaseArchive" -ForegroundColor Green
    if (Test-Path -LiteralPath $ExtensionArchive) {
        Write-Host "Optional model export archive: $ExtensionArchive" -ForegroundColor Green
    }
}
catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
