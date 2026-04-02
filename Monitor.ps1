<#
.SYNOPSIS
Deprecated compatibility stub for legacy PowerShell launcher flows.
.DESCRIPTION
Monitor.ps1 is an official cleanup target and is no longer a supported runtime entrypoint.
Use start_monitor.bat or SystemResourceMonitor*.exe start instead.
#>

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$startBat = Join-Path $scriptDir "start_monitor.bat"
$portableExe = Get-ChildItem -Path $scriptDir -Filter "SystemResourceMonitor*.exe" -File -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

Write-Warning "Monitor.ps1는 공식 정리 대상이며 새 실행 기준이 아닙니다."
Write-Host "권장 실행 경로:" -ForegroundColor Yellow
Write-Host "  1. 같은 폴더의 start_monitor.bat" -ForegroundColor Yellow
Write-Host "  2. SystemResourceMonitor*.exe start" -ForegroundColor Yellow
Write-Host "  3. 개발 환경에서는 .\venv\Scripts\python cli.py start" -ForegroundColor Yellow

if ((Test-Path $startBat) -and $portableExe) {
    Write-Host ""
    Write-Host "호환성 목적으로 start_monitor.bat로 전달합니다..." -ForegroundColor Cyan
    & $startBat
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "자동 전달 가능한 릴리스 묶음을 찾지 못했습니다." -ForegroundColor Red
exit 1
