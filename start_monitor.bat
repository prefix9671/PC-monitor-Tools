@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
:: ============================================================================
:: Name: start_monitor.bat
:: Description: Wrapper to launch the packaged System Collector portable executable
:: ============================================================================

echo ====================================================
echo   Starting System Resource Collector (Portable EXE)
echo ====================================================

:: Check for Administrator privileges
net session >nul 2>&1
if %errorLevel% NEQ 0 (
    echo [ERROR] Please run this script as Administrator.
    echo Right-click the file and select "Run as administrator".
    pause
    exit /b 1
)

:: Find the SystemResourceMonitor executable in the current directory
set "TARGET_EXE="
for %%F in (SystemResourceMonitor*.exe) do (
    set "TARGET_EXE=%%F"
    goto found_exe
)

:found_exe
if "%TARGET_EXE%"=="" (
    echo [ERROR] Could not find SystemResourceMonitor*.exe in %~dp0
    pause
    exit /b 1
)

echo Checking PawnIO driver package...
"%~dp0%TARGET_EXE%" install-pawnio --check-only
set "PAWNIO_STATUS=!ERRORLEVEL!"
if "!PAWNIO_STATUS!"=="2" (
    echo [WARN] PawnIO is not installed. CPU core temperature may be unavailable.
    echo [INFO] Manual installer helper: %~dp0install_pawnio.bat
    echo [INFO] Bundled setup file: %~dp0pawnio-bundle\PawnIO_setup.exe
    choice /M "Install bundled PawnIO now"
    if !ERRORLEVEL! EQU 1 (
        "%~dp0%TARGET_EXE%" install-pawnio
        if !ERRORLEVEL! NEQ 0 (
            echo [WARN] PawnIO installation did not complete successfully. Continuing with fallback providers.
            echo [INFO] You can retry later by running install_pawnio.bat as Administrator.
        )
    ) else (
        echo [INFO] Skipping PawnIO installation. Continuing with fallback providers.
        echo [INFO] You can install later by running install_pawnio.bat as Administrator.
    )
) else if not "!PAWNIO_STATUS!"=="0" (
    echo [WARN] PawnIO status check failed. Continuing with fallback providers.
    echo [INFO] If CPU temperature is unavailable, run install_pawnio.bat as Administrator.
)

:: Run the Portable Collector
echo Launching %TARGET_EXE% start...
"%~dp0%TARGET_EXE%" start

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Collector exited with an error.
    pause
)
