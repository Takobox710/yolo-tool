@echo off
setlocal

cd /d "%~dp0"
where pwsh.exe >nul 2>&1
if errorlevel 1 (
    echo PowerShell 7 pwsh.exe was not found. Install PowerShell 7 and retry.
    pause
    exit /b 1
)

pwsh.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer\packaging_menu.ps1"
exit /b %ERRORLEVEL%
