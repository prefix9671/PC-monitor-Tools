param(
    [string]$RemoteName = "origin",
    [switch]$Json
)

$ErrorActionPreference = "Stop"

function Invoke-GitText {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Args
    )

    $output = & git @Args 2>$null
    if ($LASTEXITCODE -ne 0) {
        return $null
    }

    return (($output | Out-String).Trim())
}

function Convert-RemoteUrlToHttps {
    param(
        [string]$RemoteUrl
    )

    if (-not $RemoteUrl) {
        return $null
    }

    if ($RemoteUrl -match "^https://") {
        return $RemoteUrl
    }

    if ($RemoteUrl -match "^git@github\.com:(.+?)(\.git)?$") {
        return "https://github.com/$($Matches[1])"
    }

    return $null
}

$repoRoot = Invoke-GitText @("rev-parse", "--show-toplevel")
if (-not $repoRoot) {
    throw "This command must be run inside a Git repository."
}

$branchName = Invoke-GitText @("rev-parse", "--abbrev-ref", "HEAD")
$remoteUrl = Invoke-GitText @("remote", "get-url", $RemoteName)
$aliasCl = Invoke-GitText @("config", "--get", "alias.cl")
$gitClCommand = Get-Command git-cl -ErrorAction SilentlyContinue
$gitClPath = if ($gitClCommand) { $gitClCommand.Source } else { $null }

$remoteKind = "unknown"
if ($remoteUrl -match "github\.com[:/]") {
    $remoteKind = "github"
} elseif ($remoteUrl -match "googlesource\.com|gerrit") {
    $remoteKind = "gerrit"
}

$status = "missing"
$recommendation = "Install depot_tools and make sure git-cl is on PATH before using Gerrit-style git cl commands."

if ($gitClPath) {
    $status = "available"
    $recommendation = "git-cl is available in PATH."
} elseif ($remoteKind -eq "github") {
    $status = "not-required"
    $recommendation = "This repository uses a GitHub remote. Use git push and a GitHub pull request instead of git cl."
}

$suggestedPrUrl = $null
$remoteHttpsUrl = Convert-RemoteUrlToHttps -RemoteUrl $remoteUrl
if ($remoteKind -eq "github" -and $remoteHttpsUrl -and $branchName -and $branchName -ne "HEAD") {
    $suggestedPrUrl = "$($remoteHttpsUrl.TrimEnd('.git'))/compare/$branchName`?expand=1"
}

$payload = [ordered]@{
    repository_root = $repoRoot
    branch = $branchName
    remote_name = $RemoteName
    remote_url = $remoteUrl
    remote_kind = $remoteKind
    git_cl_found = [bool]$gitClPath
    git_cl_path = $gitClPath
    git_alias_cl = $aliasCl
    status = $status
    recommendation = $recommendation
    suggested_pr_url = $suggestedPrUrl
}

if ($Json) {
    $payload | ConvertTo-Json -Depth 3
} else {
    Write-Output "Repository: $($payload.repository_root)"
    Write-Output "Branch: $($payload.branch)"
    Write-Output "Remote: $($payload.remote_name)"
    Write-Output "Remote URL: $($payload.remote_url)"
    Write-Output "Remote Kind: $($payload.remote_kind)"
    Write-Output "git-cl Found: $($payload.git_cl_found)"
    if ($payload.git_cl_path) {
        Write-Output "git-cl Path: $($payload.git_cl_path)"
    }
    if ($payload.git_alias_cl) {
        Write-Output "git alias cl: $($payload.git_alias_cl)"
    }
    Write-Output "Status: $($payload.status)"
    Write-Output "Recommendation: $($payload.recommendation)"
    if ($payload.suggested_pr_url) {
        Write-Output "Suggested PR URL: $($payload.suggested_pr_url)"
    }
}

if ($status -eq "missing") {
    exit 1
}

exit 0
