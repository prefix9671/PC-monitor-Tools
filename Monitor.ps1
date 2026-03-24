<#
.SYNOPSIS
Wrapper for the Python System Collector.
.DESCRIPTION
This script acts as a backwards-compatible PowerShell wrapper to launch the Python-based collector.
#>
$ErrorActionPreference = "Stop"
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "  Starting System Resource Collector via PowerShell " -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

# Require Admin Rights
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[ERROR] This script requires Administrator privileges to monitor all processes." -ForegroundColor Red
    Write-Host "Please restart PowerShell as Administrator and try again." -ForegroundColor Yellow
    Exit
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

try {
    Write-Host "Launching Python Collector..." -ForegroundColor Green
    & "$ScriptDir\venv\Scripts\python.exe" "$ScriptDir\collector_main.py"
} catch {
    Write-Host "[ERROR] Failed to start the Python collector." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}
