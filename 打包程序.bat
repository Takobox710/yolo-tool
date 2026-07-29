@echo off
setlocal

cd /d "%~dp0"
echo Packaging mode:
echo   Press Enter for program and base environment only.
echo   Type anything and press Enter for the full release, including extra environment.
set /p "PACKAGE_MODE=Select packaging mode: "
echo.
if defined PACKAGE_MODE (
    echo Building full release: setup, base environment, and extra environment.
    set "PACKAGE_ARGS=-BuildBaseRuntimeModels -BuildModelExportRuntime"
) else (
    echo Building program and base environment setup; skipping extra environment.
    set "PACKAGE_ARGS=-BuildBaseRuntimeModels"
)
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer\package_windows.ps1" %PACKAGE_ARGS%
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo Packaging failed. Exit code: %EXIT_CODE%
)

pause
exit /b %EXIT_CODE%
