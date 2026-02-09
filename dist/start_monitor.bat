@echo off
setlocal enabledelayedexpansion

:: ==========================================
:: Configuration
:: ==========================================
set "LOG_DIR=C:\SystemLogs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: Get Date for filenames using PowerShell (more robust than wmic)
for /f %%a in ('powershell -Command "Get-Date -Format yyyyMMdd"') do set DATE_STAMP=%%a
for /f %%a in ('powershell -Command "Get-Date -Format HHmmss"') do set TIME_STAMP=%%a

:: accept intervals from arguments
:: %1: Logman Interval (Global), default 1
:: %2: PowerShell Interval (Process), default 30
set "LOGMAN_SESSION=Global_Peak_Log"
set "LOGMAN_FILE=%LOG_DIR%\Global_Usage_%DATE_STAMP%_%TIME_STAMP%"
set "LOGMAN_INTERVAL=%~1"
if "%LOGMAN_INTERVAL%"=="" set "LOGMAN_INTERVAL=1"

set "PROCESS_INTERVAL=%~2"
if "%PROCESS_INTERVAL%"=="" set "PROCESS_INTERVAL=30"

:: ==========================================
:: 1. Start Logman (Global Counters)
:: ==========================================
echo Starting Logman (High Frequency Monitor: %LOGMAN_INTERVAL%s)...

:: Check if session exists and stop it
logman stop %LOGMAN_SESSION% >nul 2>&1
logman delete %LOGMAN_SESSION% >nul 2>&1

:: Create new counter
:: Capture: CPU, Available Mem, Disk Time, Disk Queue
:: NOTE: Use single -c followed by list of counters
logman create counter %LOGMAN_SESSION% -si %LOGMAN_INTERVAL% -o "%LOGMAN_FILE%" -f csv -v mmddhhmm ^
-c "\Processor(_Total)\%% Processor Time" "\Memory\Available MBytes" "\Memory\Committed Bytes" "\LogicalDisk(*)\%% Disk Time" "\LogicalDisk(*)\Current Disk Queue Length" "\LogicalDisk(*)\Disk Read Bytes/sec" "\LogicalDisk(*)\Disk Write Bytes/sec"

logman start %LOGMAN_SESSION%
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to start Logman. Run as Administrator.
    pause
    exit /b
)

:: ==========================================
:: 2. Start PowerShell (Process Details)
:: ==========================================
echo Starting PowerShell Monitor (Process Details: %PROCESS_INTERVAL%s)...

:: Resolve path to Monitor.ps1 (handles dev vs exe environment)
if exist "%~dp0Monitor.ps1" (
    set "SCRIPT_PATH=%~dp0Monitor.ps1"
) else (
    set "SCRIPT_PATH=Monitor.ps1"
)

:: Run PowerShell in a new window, keep it open
start "Process Monitor" powershell -NoProfile -ExecutionPolicy Bypass -Command "& '%SCRIPT_PATH%' -IntervalSeconds %PROCESS_INTERVAL%"

:: ==========================================
:: 3. Cleanup on Exit
:: ==========================================
echo.
echo ========================================================
echo  Monitoring Running...
echo  - Logman: 1s interval (Global)
echo  - PowerShell: 30s interval (Process)
echo  Press any key to STOP monitoring and exit.
echo ========================================================
pause >nul

echo Stopping Logman...
logman stop %LOGMAN_SESSION%
logman delete %LOGMAN_SESSION%

echo Done.
