@echo off
setlocal enabledelayedexpansion

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
if exist "dist\%BASENAME%.exe" (
    set /a "REV+=1"
    goto check_rev
)

echo ========================================
echo   Building and Renaming to: %BASENAME%.exe
echo ========================================

:: 3. Run PyInstaller (using existing spec)
pyinstaller --clean monitor.spec

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Build failed!
    pause
    exit /b %ERRORLEVEL%
)

:: 4. Rename output file
:: monitor.spec produces SystemResourceMonitor.exe based on its content
if exist "dist\SystemResourceMonitor.exe" (
    echo Renaming dist\SystemResourceMonitor.exe to dist\%BASENAME%.exe
    move "dist\SystemResourceMonitor.exe" "dist\%BASENAME%.exe"
)

:: 5. Git Push
echo Pushing to GitHub...
git add .
git commit -m "Build update: %BASENAME%"
git push

echo ========================================
echo   Build Completed: dist/%BASENAME%.exe
echo ========================================
pause
