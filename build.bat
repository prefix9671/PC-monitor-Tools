@echo off
setlocal enabledelayedexpansion

set "ARTIFACT_ROOT=.artifacts"
set "MANUAL_SITE_DIR=%ARTIFACT_ROOT%\manual-site"
set "PYI_BUILD_DIR=%ARTIFACT_ROOT%\pyinstaller\build"
set "PYI_DIST_DIR=%ARTIFACT_ROOT%\pyinstaller\dist"
set "RELEASE_ROOT=%ARTIFACT_ROOT%\releases"

if not exist "%ARTIFACT_ROOT%" mkdir "%ARTIFACT_ROOT%"
if not exist "%RELEASE_ROOT%" mkdir "%RELEASE_ROOT%"

:: 1. Get current date (fallback if wmic fails)
echo. | date > nul
for /f "tokens=1-3 delims=-/. " %%a in ("%date%") do (
    set "DATE_STAMP=%%a%%b%%c"
)
:: Remove potential spaces or non-digits
set "DATE_STAMP=%DATE_STAMP: =%"

:: 2. Find appropriate revision
set "REV=1"
:check_rev
set "BASENAME=SystemResourceMonitor%DATE_STAMP%_rev%REV%"
if exist "%RELEASE_ROOT%\%BASENAME%" (
    set /a "REV+=1"
    goto check_rev
)

set "RELEASE_DIR=%RELEASE_ROOT%\%BASENAME%"

echo ========================================
echo   Building Web Manual (MkDocs)
echo ========================================
call .\venv\Scripts\python.exe -m mkdocs build

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] MkDocs build failed!
    pause
    exit /b %ERRORLEVEL%
)

echo ========================================
echo   Preparing LibreHardwareMonitor Bundle
echo ========================================
call .\venv\Scripts\python.exe scripts\prepare_lhm_bundle.py

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] LibreHardwareMonitor bundle preparation failed!
    pause
    exit /b %ERRORLEVEL%
)

echo ========================================
echo   Building and Renaming to: %BASENAME%.exe
echo ========================================

if exist "%RELEASE_DIR%" rmdir /S /Q "%RELEASE_DIR%"
mkdir "%RELEASE_DIR%"

:: 3. Run PyInstaller (using existing spec)
.\venv\Scripts\pyinstaller.exe --clean --workpath "%PYI_BUILD_DIR%" --distpath "%PYI_DIST_DIR%" monitor.spec

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Build failed!
    pause
    exit /b %ERRORLEVEL%
)

:: 4. Rename output file
:: monitor.spec produces SystemResourceMonitor.exe based on its content
if exist "%PYI_DIST_DIR%\SystemResourceMonitor.exe" (
    echo Moving %PYI_DIST_DIR%\SystemResourceMonitor.exe to %RELEASE_DIR%\%BASENAME%.exe
    move "%PYI_DIST_DIR%\SystemResourceMonitor.exe" "%RELEASE_DIR%\%BASENAME%.exe"
)

:: 5. Copy supported launchers to release bundle
echo Copying release scripts...
copy "start_monitor.bat" "%RELEASE_DIR%\" >nul

:: 6. Zip Manual (.artifacts/manual-site) to release bundle
echo Zipping Manual...
if exist "%RELEASE_DIR%\Manual.zip" del "%RELEASE_DIR%\Manual.zip"
powershell.exe -NoProfile -Command "Compress-Archive -Path '%MANUAL_SITE_DIR%\*' -DestinationPath '%RELEASE_DIR%\Manual.zip' -Force"



echo ========================================
echo   Build Completed: 
echo   - %RELEASE_DIR%\%BASENAME%.exe
echo   - %RELEASE_DIR%\start_monitor.bat
echo   - %RELEASE_DIR%\Manual.zip
echo ========================================
:: pause
