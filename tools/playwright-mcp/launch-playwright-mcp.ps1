param(
    [switch]$Headless = $true,
    [switch]$Isolated = $true,
    [string]$Browser = "msedge",
    [int]$Port = 0
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
$nodeExe = "C:\Program Files\nodejs\node.exe"
$npmCmd = "C:\Program Files\nodejs\npm.cmd"
$cliPath = Join-Path $scriptDir "node_modules\@playwright\mcp\cli.js"
$npmCacheDir = Join-Path $scriptDir ".npm-cache"

function Write-McpLog {
    param([string]$Message)
    [Console]::Error.WriteLine($Message)
}

if (-not (Test-Path $nodeExe)) {
    throw "Node.js runtime not found at $nodeExe"
}

if (-not (Test-Path $cliPath)) {
    if (-not (Test-Path $npmCmd)) {
        throw "npm not found at $npmCmd"
    }

    Write-McpLog "[playwright-mcp] Installing local dependencies..."
    & $npmCmd install --no-fund --no-audit --cache $npmCacheDir
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install @playwright/mcp dependencies."
    }
}

$arguments = @($cliPath, "--browser=$Browser")

if ($Headless) {
    $arguments += "--headless"
}

if ($Isolated) {
    $arguments += "--isolated"
}

if ($Port -gt 0) {
    $arguments += "--port"
    $arguments += "$Port"
}

Write-McpLog "[playwright-mcp] Launching from $repoRoot"
& $nodeExe @arguments
exit $LASTEXITCODE
