$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

function Invoke-PackagingScript {
    param(
        [Parameter(Mandatory)]
        [string]$RelativePath,
        [string[]]$Arguments = @()
    )

    $scriptPath = Join-Path $Root $RelativePath
    & $scriptPath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "打包脚本失败：$RelativePath，退出码：$LASTEXITCODE"
    }
}

function Wait-And-Exit {
    param([int]$Code)

    Read-Host "按 Enter 键退出" | Out-Null
    exit $Code
}

try {
    Write-Host ""
    Write-Host "=== YOLOTool Windows 打包工具 ===" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "[1] GPU + CPU 全量打包"
    Write-Host "[2] GPU 版全量打包"
    Write-Host "[3] GPU 基础包 - 单卷"
    Write-Host "[4] GPU 基础包 - 分卷，每卷小于 1 GiB"
    Write-Host "[5] GPU 附加包 - 单卷"
    Write-Host "[6] GPU 附加包 - 分卷，每卷小于 1 GiB"
    Write-Host "[7] GPU 程序包 - 复用已有环境包"
    Write-Host "[8] CPU 版本打包"
    Write-Host "[9] 本地开发快包"
    Write-Host "[Q] 退出"
    Write-Host ""
    Write-Host "请选择操作 [1/2/3/4/5/6/7/8/9/Q]: " -NoNewline -ForegroundColor Yellow
    $selection = [Console]::ReadKey($true).KeyChar.ToString().ToUpperInvariant()
    Write-Host $selection

    switch ($selection) {
        "1" {
            Write-Host "正在执行 GPU 全量打包，完成后继续执行 CPU 全量打包..." -ForegroundColor Cyan
            Invoke-PackagingScript "installer\package_windows.ps1" @(
                "-BuildBaseRuntimeModels", "-BuildModelExportRuntime", "-Clean"
            )
            Invoke-PackagingScript "installer\package_windows.ps1" @(
                "-Variant", "CPU", "-BuildBaseRuntimeModels", "-Clean"
            )
        }
        "2" {
            Write-Host "正在执行 GPU 版全量打包..." -ForegroundColor Cyan
            Invoke-PackagingScript "installer\package_windows.ps1" @(
                "-BuildBaseRuntimeModels", "-BuildModelExportRuntime", "-Clean"
            )
        }
        "3" {
            Write-Host "正在打包 GPU 基础包 - 单卷..." -ForegroundColor Cyan
            Invoke-PackagingScript "installer\build_windows.ps1" @(
                "-Mode", "release", "-Variant", "GPU", "-Clean"
            )
            Invoke-PackagingScript "installer\build_base_runtime_models.ps1" @(
                "-Variant", "GPU", "-Clean"
            )
        }
        "4" {
            Write-Host "正在打包 GPU 基础包 - 分卷..." -ForegroundColor Cyan
            Invoke-PackagingScript "installer\build_windows.ps1" @(
                "-Mode", "release", "-Variant", "GPU", "-Clean"
            )
            Invoke-PackagingScript "installer\build_base_runtime_models.ps1" @(
                "-Variant", "GPU", "-Clean", "-SplitBaseArchive"
            )
        }
        "5" {
            Write-Host "正在打包 GPU 附加包 - 单卷..." -ForegroundColor Cyan
            Invoke-PackagingScript "installer\build_model_export_runtime.ps1" @(
                "-Clean"
            )
        }
        "6" {
            Write-Host "正在打包 GPU 附加包 - 分卷..." -ForegroundColor Cyan
            Invoke-PackagingScript "installer\build_model_export_runtime.ps1" @(
                "-Clean", "-SplitArchive"
            )
        }
        "7" {
            Write-Host "正在打包 GPU 程序包 - 复用已有环境包..." -ForegroundColor Cyan
            Invoke-PackagingScript "installer\package_windows.ps1"
        }
        "8" {
            Write-Host "正在执行 CPU 版本打包..." -ForegroundColor Cyan
            Invoke-PackagingScript "installer\package_windows.ps1" @(
                "-Variant", "CPU", "-BuildBaseRuntimeModels", "-Clean"
            )
        }
        "9" {
            Write-Host "正在执行本地开发快包..." -ForegroundColor Cyan
            Invoke-PackagingScript "installer\build_windows.ps1" @(
                "-Mode", "dev"
            )
        }
        "Q" {
            exit 0
        }
        default {
            throw "无效操作：$selection"
        }
    }

    Write-Host ""
    Write-Host "打包完成。" -ForegroundColor Green
    Wait-And-Exit 0
}
catch {
    Write-Host "" 
    Write-Host "打包失败：$($_.Exception.Message)" -ForegroundColor Red
    Wait-And-Exit 1
}
