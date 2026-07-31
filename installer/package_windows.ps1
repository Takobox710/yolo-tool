param(
    [switch]$Clean,
    [switch]$BuildBaseRuntimeModels,
    [switch]$BuildModelExportRuntime,
    [switch]$SkipModelExportRuntime,
    [ValidateSet("GPU", "CPU")]
    [string]$Variant = "GPU",
    [ValidateSet("Program", "Full", "AppUpdate", "RuntimeFull")]
    [string]$PackageType = "Program",
    [string]$RuntimeVersion = "",
    [string]$RequiredRuntimeVersion = "",
    [switch]$SplitBaseArchive
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$InstallerScript = Join-Path $PSScriptRoot "yolo_tool.iss"
$InstallerOutputDir = Join-Path $PSScriptRoot "output"

function Write-Step {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Cyan
}

function Format-Elapsed {
    param([System.Diagnostics.Stopwatch]$Stopwatch)
    if ($Stopwatch.Elapsed.TotalMinutes -ge 1) {
        return "{0} 分 {1:N2} 秒" -f [math]::Floor($Stopwatch.Elapsed.TotalMinutes), $Stopwatch.Elapsed.Seconds
    }
    return "{0:N2} 秒" -f $Stopwatch.Elapsed.TotalSeconds
}

function Write-StepElapsed {
    param(
        [string]$Message,
        [System.Diagnostics.Stopwatch]$Stopwatch
    )
    Write-Step "$Message，耗时：$(Format-Elapsed $Stopwatch)"
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
    $RuntimeEnvironment = if ($Variant -eq "CPU") { "release-cpu" } else { "release-base" }
    $ArtifactPrefix = if ($Variant -eq "CPU") { "YOLOTool_CPU" } else { "YOLOTool" }
    $IntegratedRuntime = $Variant -eq "CPU"
    if ($IntegratedRuntime -and $SplitBaseArchive) {
        throw "CPU 版使用一体式安装包，不支持生成基础环境分卷。"
    }
    if ($Variant -eq "CPU" -and $BuildModelExportRuntime) {
        throw "CPU 版不支持构建模型转换附加环境；OpenVINO、NCNN、PNNX 已并入 CPU 基础环境。"
    }
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
    $BaseStaging = Join-Path $Root "dist\packages\BaseRuntimeModels-CPU"
    $BaseArchivePath = Join-Path $InstallerOutputDir "${ArtifactPrefix}_BaseEnv_${BaseVersion}.7z"
    $BaseArchiveFirstVolume = "${BaseArchivePath}.001"
    $BaseArchive = if ($SplitBaseArchive -and (Test-Path -LiteralPath $BaseArchiveFirstVolume)) {
        $BaseArchiveFirstVolume
    } elseif (Test-Path -LiteralPath $BaseArchivePath) {
        $BaseArchivePath
    } elseif (Test-Path -LiteralPath $BaseArchiveFirstVolume) {
        $BaseArchiveFirstVolume
    } elseif ($SplitBaseArchive) {
        $BaseArchiveFirstVolume
    } else {
        $BaseArchivePath
    }
    if (-not $IntegratedRuntime -and -not $BuildBaseRuntimeModels -and -not (Test-Path -LiteralPath $BaseArchive)) {
        throw "Required base archive is missing: $BaseArchive. Run the full packaging entry first."
    }

    $ProgramOnly = -not $BuildBaseRuntimeModels
    if ($ProgramOnly) {
        Write-Step "[1/5] 正在构建仅程序 EXE 和程序 staging..."
    } else {
        Write-Step "[1/5] 正在构建完整冻结程序和程序 staging..."
    }
    $ProgramStepTimer = [System.Diagnostics.Stopwatch]::StartNew()
    & (Join-Path $PSScriptRoot "build_windows.ps1") `
        -Mode release -Clean:$Clean -PackageType Program `
        -ProgramOnly:$ProgramOnly `
        -Variant $Variant `
        -RuntimeVersion $RuntimeVersion -RequiredRuntimeVersion $RequiredRuntimeVersion
    if ($LASTEXITCODE -ne 0) {
        throw "Program build failed with exit code $LASTEXITCODE"
    }
    $ProgramStepTimer.Stop()
    Write-StepElapsed "[1/5] 程序和 staging 构建完成" $ProgramStepTimer

    if ($BuildBaseRuntimeModels) {
        $BaseStepTimer = [System.Diagnostics.Stopwatch]::StartNew()
        if ($IntegratedRuntime) {
            Write-Step "[2/5] 正在构建 CPU 一体式安装包运行时 staging..."
            & (Join-Path $PSScriptRoot "build_base_runtime_models.ps1") `
                -Clean:$Clean -Variant $Variant -RuntimeVersion $RuntimeVersion `
                -NoArchive
        } else {
            Write-Step "[2/5] 正在构建基础环境和模型归档..."
            & (Join-Path $PSScriptRoot "build_base_runtime_models.ps1") `
                -Clean:$Clean -Variant $Variant -RuntimeVersion $RuntimeVersion `
                -SplitBaseArchive:$SplitBaseArchive
        }
        if ($LASTEXITCODE -ne 0) {
            throw "Base runtime and models build failed with exit code $LASTEXITCODE"
        }
        $BaseStepTimer.Stop()
        Write-StepElapsed "[2/5] 基础环境包步骤完成" $BaseStepTimer

        # The full frozen output above is the source for BaseEnv. The installer
        # must still carry a runtime-free program EXE so it does not duplicate
        # Python and third-party modules already owned by BaseEnv.
        $ProgramOnlyStepTimer = [System.Diagnostics.Stopwatch]::StartNew()
        Write-Step "[3/5] 正在重新构建仅程序 EXE 和程序 staging..."
        & (Join-Path $PSScriptRoot "build_windows.ps1") `
            -Mode release -Clean -PackageType Program `
            -ProgramOnly `
            -Variant $Variant `
            -RuntimeVersion $RuntimeVersion -RequiredRuntimeVersion $RequiredRuntimeVersion
        if ($LASTEXITCODE -ne 0) {
            throw "Program-only build failed after base runtime build with exit code $LASTEXITCODE"
        }
        $ProgramOnlyStepTimer.Stop()
        Write-StepElapsed "[3/5] 仅程序 EXE 和 staging 构建完成" $ProgramOnlyStepTimer
    }
    if ($BuildModelExportRuntime) {
        $ExtensionStepTimer = [System.Diagnostics.Stopwatch]::StartNew()
        Write-Step "[4/5] 正在构建附加模型转换环境归档..."
        & (Join-Path $PSScriptRoot "build_model_export_runtime.ps1") -Clean:$Clean
        if ($LASTEXITCODE -ne 0) {
            throw "Model export runtime build failed with exit code $LASTEXITCODE"
        }
        $ExtensionStepTimer.Stop()
        Write-StepElapsed "[4/5] 附加环境包步骤完成" $ExtensionStepTimer
    }

    if (-not $IntegratedRuntime -and -not (Test-Path -LiteralPath $BaseArchive)) {
        throw "Required base archive is missing: $BaseArchive. Re-run with -BuildBaseRuntimeModels."
    }
    if ($IntegratedRuntime -and $BuildBaseRuntimeModels -and
        -not (Test-Path -LiteralPath (Join-Path $BaseStaging "base-package-manifest.json"))) {
        throw "CPU 一体式安装包缺少基础运行时 staging 清单：$BaseStaging"
    }
    $ExtensionVersion = ""
    $ExtensionArchive = ""
    if ($Variant -eq "GPU") {
        $ExtensionVersion = (Get-Content -LiteralPath (Join-Path $PSScriptRoot "model-export-runtime-version.txt") -Raw).Trim()
        $ExtensionArchive = Join-Path $InstallerOutputDir "YOLOTool_ExtraEnv_${ExtensionVersion}.7z"
    }
    $ProgramStaging = Join-Path $Root "dist\packages\Program"
    $CatalogPath = Join-Path $ProgramStaging "companion-catalog.json"
    if ($IntegratedRuntime -and -not $BuildBaseRuntimeModels -and
        -not (Test-Path -LiteralPath (Join-Path $BaseStaging "base-package-manifest.json"))) {
        $Catalog = [ordered]@{
            schema_version = 1
            base = [ordered]@{
                filename = ""
                integrated = $true
                package_id = "yolo-tool-base-runtime-models"
                manifest_schema = 1
                platform = "win-64"
                architecture = "x86_64"
                version = $BaseVersion
                runtime_version = $RuntimeVersion
                variant = "cpu"
                uncompressed_size = 0
            }
        }
        $Catalog | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $CatalogPath -Encoding utf8
    } else {
        $CatalogArgs = @("-m", "src.devtools.companion_catalog")
        if ($IntegratedRuntime) {
            $CatalogArgs += @("--base-staging", $BaseStaging)
        } else {
            $CatalogArgs += @("--base", $BaseArchive)
        }
        $CatalogArgs += @(
            "--variant", $Variant.ToLowerInvariant(),
            "--output", $CatalogPath
        )
        if (Test-Path -LiteralPath $ExtensionArchive) {
            $CatalogArgs += @("--extension", $ExtensionArchive)
        }
        & pixi run -e $RuntimeEnvironment python @CatalogArgs
        if ($LASTEXITCODE -ne 0) {
            throw "生成伴随包清单失败。"
        }
    }
    $Catalog = Get-Content -LiteralPath $CatalogPath -Raw | ConvertFrom-Json
    if ($Catalog.base.runtime_version -ne $RequiredRuntimeVersion) {
        throw "基础包运行时版本 '$($Catalog.base.runtime_version)' 与要求的版本 '$RequiredRuntimeVersion' 不一致。"
    }
    if ($Catalog.base.variant -ne $Variant.ToLowerInvariant()) {
        throw "基础包变体 '$($Catalog.base.variant)' 与当前构建变体 '$($Variant.ToLowerInvariant())' 不一致。"
    }
    if (-not $IntegratedRuntime -and (Test-Path -LiteralPath (Join-Path $ProgramStaging "_internal"))) {
        throw "程序 staging 异常包含 _internal；拒绝生成重复携带运行环境的安装器。"
    }

    $isccPath = Get-InnoSetupCompiler
    if (-not $isccPath) {
        throw "ISCC.exe was not found. Install Inno Setup 6.4 or newer."
    }
    $AppVersion = (& pixi run -e $RuntimeEnvironment python -c "from src import APP_VERSION; print(APP_VERSION)" | Out-String).Trim()
    $InnoArgs = @(
        "/DMyAppVersion=$AppVersion",
        "/DPackageVariant=$($Variant.ToLowerInvariant())",
        "/DArtifactPrefix=$ArtifactPrefix",
        "/DMyAppName=$(if ($Variant -eq "CPU") { "YOLOTool CPU" } else { "YOLOTool" })",
        "/DDefaultAppDirName=$(if ($Variant -eq "CPU") { "YOLOTool_CPU" } else { "YOLOTool" })",
        "/DRequiredRuntimeVersion=$RequiredRuntimeVersion",
        "/DBasePackageName=$($Catalog.base.filename)",
        "/DBasePackageVersion=$($Catalog.base.version)",
        "/DBaseRuntimeVersion=$($Catalog.base.runtime_version)",
        "/DBaseUnpackedSize=$($Catalog.base.uncompressed_size)"
    )
    if ($IntegratedRuntime) {
        $InnoArgs += "/DIntegratedRuntime=1"
        if ($BuildBaseRuntimeModels) {
            $InnoArgs += "/DIntegratedRuntimeStaging=1"
        }
    }
    if ($Catalog.model_export) {
        $InnoArgs += @(
            "/DExtensionPackageName=$($Catalog.model_export.filename)",
            "/DExtensionPackageVersion=$($Catalog.model_export.version)"
        )
    }

    $InstallerStepTimer = [System.Diagnostics.Stopwatch]::StartNew()
    Write-Step "[5/5] 正在构建统一安装包..."
    New-Item -ItemType Directory -Force -Path $InstallerOutputDir | Out-Null
    & $isccPath @InnoArgs $InstallerScript
    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup build failed with exit code $LASTEXITCODE"
    }
    $InstallerStepTimer.Stop()
    Write-StepElapsed "[5/5] 安装包构建完成" $InstallerStepTimer

    Write-Step "[5/5] 打包完成。"
    Write-Host "安装包：$(Join-Path $InstallerOutputDir "${ArtifactPrefix}_Setup_${AppVersion}.exe")" -ForegroundColor Green
    if ($IntegratedRuntime) {
        Write-Host "CPU 一体式运行时 staging：$BaseStaging" -ForegroundColor Green
    } else {
        Write-Host "基础环境包：$BaseArchive" -ForegroundColor Green
    }
    if (Test-Path -LiteralPath $ExtensionArchive) {
        Write-Host "附加环境包：$ExtensionArchive" -ForegroundColor Green
    }
}
catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
