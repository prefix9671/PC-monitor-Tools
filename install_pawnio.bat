@echo off
setlocal
cd /d "%~dp0"
:: ============================================================================
:: Name: install_pawnio.bat
:: Description: Install the bundled PawnIO driver package for CPU temperature sensors
:: ============================================================================

echo ====================================================
echo   Installing PawnIO Driver Package
echo ====================================================

net session >nul 2>&1
if %errorLevel% NEQ 0 (
    echo [INFO] Requesting Administrator privileges...
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b 0
)

set "TARGET_EXE="
for %%F in (SystemResourceMonitor*.exe) do (
    set "TARGET_EXE=%%F"
    goto found_exe
)

:found_exe
if not "%TARGET_EXE%"=="" (
    echo Using %TARGET_EXE% install-pawnio...
    "%~dp0%TARGET_EXE%" install-pawnio
    exit /b %ERRORLEVEL%
)

if exist "%~dp0pawnio-bundle\PawnIO_setup.exe" (
    echo Using pawnio-bundle\PawnIO_setup.exe...
    "%~dp0pawnio-bundle\PawnIO_setup.exe" -install
    exit /b %ERRORLEVEL%
)

echo [ERROR] Could not find SystemResourceMonitor*.exe or pawnio-bundle\PawnIO_setup.exe in %~dp0
exit /b 1
