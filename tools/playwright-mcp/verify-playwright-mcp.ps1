param(
    [int]$Port = 8931
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$launcher = Join-Path $scriptDir "launch-playwright-mcp.ps1"
$job = $null

try {
    $job = Start-Job -ScriptBlock {
        param($launchPath, $listenPort)
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $launchPath -Port $listenPort
    } -ArgumentList $launcher, $Port

    Start-Sleep -Seconds 8

    $listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $listener) {
        throw "Playwright MCP server did not start listening on port $Port."
    }

    Write-Host "[playwright-mcp] Server is listening on port $Port (address $($listener.LocalAddress))"
}
catch {
    throw
}
finally {
    if ($job) {
        Stop-Job -Job $job -ErrorAction SilentlyContinue | Out-Null
        Receive-Job -Job $job -ErrorAction SilentlyContinue | Out-Null
        Remove-Job -Job $job -Force -ErrorAction SilentlyContinue | Out-Null
    }
}
