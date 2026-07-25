@echo off
setlocal

cd /d "%~dp0"
echo Building program update setup with existing environment archives.
echo.
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer\package_windows.ps1"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo Packaging failed. Exit code: %EXIT_CODE%
)

pause
exit /b %EXIT_CODE%
