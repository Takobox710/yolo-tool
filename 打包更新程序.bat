@echo off
setlocal

cd /d "%~dp0"
echo Building GPU program update setup with existing environment archives.
echo To update a CPU installation, run package_windows.ps1 with -Variant CPU.
echo.
where pwsh.exe >nul 2>&1
if errorlevel 1 (
    echo PowerShell 7 pwsh.exe was not found. Install PowerShell 7 and retry.
    exit /b 1
)
pwsh.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer\package_windows.ps1"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo Packaging failed. Exit code: %EXIT_CODE%
)

pause
exit /b %EXIT_CODE%
