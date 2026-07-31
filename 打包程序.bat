@echo off
setlocal

cd /d "%~dp0"
echo Packaging mode:
echo   Press Enter for GPU program and base environment only.
echo   Type G and press Enter for the GPU full release, including extra environment.
echo   Type C and press Enter for the CPU release (no extra environment).
set /p "PACKAGE_MODE=Select packaging mode: "
echo.
if /i "%PACKAGE_MODE%"=="C" (
    echo Building CPU release: setup and CPU base environment.
    set "PACKAGE_ARGS=-Variant CPU -BuildBaseRuntimeModels"
) else if /i "%PACKAGE_MODE%"=="G" (
    echo Building full release: setup, base environment, and extra environment.
    set "PACKAGE_ARGS=-BuildBaseRuntimeModels -BuildModelExportRuntime"
) else (
    echo Building program and base environment setup; skipping extra environment.
    set "PACKAGE_ARGS=-BuildBaseRuntimeModels"
)
where pwsh.exe >nul 2>&1
if errorlevel 1 (
    echo PowerShell 7 pwsh.exe was not found. Install PowerShell 7 and retry.
    exit /b 1
)
pwsh.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer\package_windows.ps1" %PACKAGE_ARGS%
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo Packaging failed. Exit code: %EXIT_CODE%
)

pause
exit /b %EXIT_CODE%
