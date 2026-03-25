@echo off
setlocal enabledelayedexpansion
:: ==========================================
:: Name: test_portable.bat
:: Description: Verifies the packaged EXE runs the collector in a clean directory
:: ==========================================
set "TEST_DIR=C:\temp\monitor_portable_test"
set "DIST_DIR=%~dp0dist"

echo ==========================================
echo [1] Preparing Clean Environment
echo ==========================================
if exist "%TEST_DIR%" (
    echo Cleaning up old test directory...
    rmdir /S /Q "%TEST_DIR%"
)
mkdir "%TEST_DIR%"
mkdir "%TEST_DIR%\logs"

echo ==========================================
echo [2] Locating Latest Executable
echo ==========================================
set "TARGET_EXE="
for %%F in ("%DIST_DIR%\SystemResourceMonitor*.exe") do (
    set "TARGET_EXE=%%~nxF"
)

if "%TARGET_EXE%"=="" (
    echo [ERROR] No SystemResourceMonitor*.exe found in dist\
    exit /b 1
)

echo Found: %TARGET_EXE%
copy "%DIST_DIR%\%TARGET_EXE%" "%TEST_DIR%\" >nul
copy "%DIST_DIR%\start_monitor.bat" "%TEST_DIR%\" >nul

echo ==========================================
echo [3] Executing Portable Collector Test
echo ==========================================
echo Running: %TARGET_EXE% start --iterations 6 --out-dir logs
cd /d "%TEST_DIR%"

"%TARGET_EXE%" start --iterations 6 --out-dir logs

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Portable execution failed! (Exit Code: %ERRORLEVEL%)
    exit /b %ERRORLEVEL%
)

echo ==========================================
echo [4] Verifying Log Generation
echo ==========================================
set /a LOG_COUNT=0
for %%F in (logs\*.csv) do (
    set /a LOG_COUNT+=1
    echo Found log: %%~nxF
)

if %LOG_COUNT% EQU 0 (
    echo [ERROR] No CSV logs were generated!
    exit /b 1
)

echo ==========================================
echo [SUCCESS] Portable CLI test passed!
echo The universal entrypoint correctly handles 'start' outside the venv.
echo Test directory: %TEST_DIR%
echo ==========================================
pause
