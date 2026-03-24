@echo off
cd /d "%~dp0"
:: ============================================================================
:: Name: start_monitor.bat
:: Description: Wrapper to launch the Python-based System Collector
:: ============================================================================

echo ====================================================
echo   Starting System Resource Collector (Python/psutil)
echo ====================================================

:: Check for Administrator privileges
net session >nul 2>&1
if %errorLevel% NEQ 0 (
    echo [ERROR] Please run this script as Administrator.
    echo Right-click the file and select "Run as administrator".
    pause
    exit /b 1
)

:: Run the Python Collector Python script
echo Launching collector_main.py...
.\venv\Scripts\python.exe collector_main.py

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Collector exited with an error.
    pause
)
