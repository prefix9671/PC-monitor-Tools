@echo off
setlocal enabledelayedexpansion

:: Get current date and time for versioning
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set TIMESTAMP=%datetime:~0,4%-%datetime:~4,2%-%datetime:~6,2% %datetime:~8,2%:%datetime:~10,2%

echo ========================================
echo   System Resource Monitor Build Script
echo   Build Time: %TIMESTAMP%
echo ========================================

:: 1. Update Build Date in config.py
echo Updating build info in config.py...
powershell -Command "(Get-Content config.py) -replace 'LAST_BUILD = \".*\"', 'LAST_BUILD = \"%TIMESTAMP%\"' | Set-Content config.py"

:: 2. Cleanup old build files
echo Cleaning up previous build artifacts...
if exist dist\SystemResourceMonitor.exe taskkill /F /IM SystemResourceMonitor.exe /T 2>nul
if exist build rd /s /q build
if exist dist rd /s /q dist

:: 3. Run PyInstaller
echo Running PyInstaller...
pyinstaller --clean monitor.spec

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Build failed!
    pause
    exit /b %ERRORLEVEL%
)

:: 4. Git Push
echo Pushing to GitHub...
git add .
git commit -m "Build update: %TIMESTAMP%"
git push

echo ========================================
echo   Build Completed Successfully!
echo   Location: dist/SystemResourceMonitor.exe
echo ========================================
pause
