@echo off
setlocal enabledelayedexpansion

:: ==========================================
:: Configuration
:: ==========================================
set "LOG_DIR=C:\SystemLogs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: Get Date for filenames
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set "DATE_STAMP=%datetime:~0,8%"
set "TIME_STAMP=%datetime:~8,6%"

set "LOGMAN_SESSION=Global_Peak_Log"
set "LOGMAN_FILE=%LOG_DIR%\Global_Usage_%DATE_STAMP%_%TIME_STAMP%"

:: ==========================================
:: 1. Start Logman (Global Counters @ 1s)
:: ==========================================
echo Starting Logman (High Frequency Monitor)...

:: Check if session exists and stop it
logman stop %LOGMAN_SESSION% >nul 2>&1
logman delete %LOGMAN_SESSION% >nul 2>&1

:: Create new counter
:: Capture: CPU, Available Mem, Disk Time, Disk Queue
logman create counter %LOGMAN_SESSION% -si 1 -o "%LOGMAN_FILE%" -f csv -v mmddhhmm ^
-c "\Processor(_Total)\%% Processor Time" ^
-c "\Memory\Available MBytes" ^
-c "\Memory\Committed Bytes" ^
-c "\LogicalDisk(_Total)\%% Disk Time" ^
-c "\LogicalDisk(_Total)\Current Disk Queue Length" ^
-c "\LogicalDisk(_Total)\Disk Read Bytes/sec" ^
-c "\LogicalDisk(_Total)\Disk Write Bytes/sec"

logman start %LOGMAN_SESSION%
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to start Logman. Run as Administrator.
    pause
    exit /b
)

:: ==========================================
:: 2. Start PowerShell (Process Details @ 30s)
:: ==========================================
echo Starting PowerShell Monitor (Process Details)...

:: Resolve path to Monitor.ps1 (handles dev vs exe environment)
if exist "%~dp0Monitor.ps1" (
    set "SCRIPT_PATH=%~dp0Monitor.ps1"
) else (
    set "SCRIPT_PATH=Monitor.ps1"
)

:: Run PowerShell in a new window, keep it open
start "Process Monitor" powershell -NoProfile -ExecutionPolicy Bypass -Command "& '%SCRIPT_PATH%' -IntervalSeconds 30"

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
