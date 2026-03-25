@echo off
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

:: Run the Portable Collector
echo Launching %TARGET_EXE% start...
"%~dp0%TARGET_EXE%" start

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Collector exited with an error.
    pause
)
