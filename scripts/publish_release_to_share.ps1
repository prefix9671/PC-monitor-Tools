param(
    [Parameter(Mandatory = $true)]
    [string]$SourceDir,

    [Parameter(Mandatory = $true)]
    [string]$ReleaseName,

    [string]$TargetServer = "192.168.1.13",
    [string]$TargetShare = "sqa",
    [string]$TargetFolderName = "",
    [string]$DefaultUsername = "qa"
)

$ErrorActionPreference = "Stop"

function Get-DefaultTargetFolderName {
    return (-join [char[]](0x31, 0x31, 0x33, 0x5F, 0xD14C, 0xC2A4, 0xD2B8, 0x20, 0xD234))
}

if (-not $TargetFolderName) {
    $TargetFolderName = Get-DefaultTargetFolderName
}

$resolvedSourceDir = (Resolve-Path -LiteralPath $SourceDir).Path
if (-not (Test-Path -LiteralPath $resolvedSourceDir -PathType Container)) {
    throw "Source directory does not exist: $SourceDir"
}

if ([string]::IsNullOrWhiteSpace($ReleaseName)) {
    throw "ReleaseName must not be empty."
}

$targetRoot = "\\{0}\{1}\{2}" -f $TargetServer, $TargetShare, $TargetFolderName
if ($targetRoot -notlike "\\*") {
    throw "TargetRoot must be a UNC path."
}

$driveName = $null

function Copy-ReleaseBundle {
    param(
        [Parameter(Mandatory = $true)]
        [string]$CopyRoot
    )

    $targetDir = Join-Path $CopyRoot $ReleaseName
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null

    Write-Host ('[INFO] Publishing release bundle to {0}\{1}' -f $CopyRoot.TrimEnd('\'), $ReleaseName)

    & robocopy $resolvedSourceDir $targetDir /E /R:2 /W:2 /NFL /NDL /NJH /NJS /NP /COPY:DAT /DCOPY:DAT
    $robocopyExitCode = $LASTEXITCODE
    if ($robocopyExitCode -gt 7) {
        throw "robocopy failed with exit code $robocopyExitCode"
    }
}

function Get-ArchiveDestinationPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ArchiveRoot,

        [Parameter(Mandatory = $true)]
        [string]$FolderName
    )

    $candidate = Join-Path $ArchiveRoot $FolderName
    if (-not (Test-Path -LiteralPath $candidate)) {
        return $candidate
    }

    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $attempt = Join-Path $ArchiveRoot ("{0}_{1}" -f $FolderName, $timestamp)
    if (-not (Test-Path -LiteralPath $attempt)) {
        return $attempt
    }

    for ($index = 2; $index -le 99; $index++) {
        $numberedAttempt = Join-Path $ArchiveRoot ("{0}_{1}_{2}" -f $FolderName, $timestamp, $index)
        if (-not (Test-Path -LiteralPath $numberedAttempt)) {
            return $numberedAttempt
        }
    }

    throw "Unable to determine archive destination path for $FolderName"
}

function Archive-PreviousReleases {
    param(
        [Parameter(Mandatory = $true)]
        [string]$CopyRoot,

        [Parameter(Mandatory = $true)]
        [string]$ActiveReleaseName
    )

    $archiveRoot = Join-Path $CopyRoot "old"
    New-Item -ItemType Directory -Path $archiveRoot -Force | Out-Null

    $previousReleaseDirs = Get-ChildItem -LiteralPath $CopyRoot -Directory | Where-Object {
        $_.Name -ne $ActiveReleaseName -and $_.Name -ne "old"
    }

    foreach ($releaseDir in $previousReleaseDirs) {
        $archiveDestination = Get-ArchiveDestinationPath -ArchiveRoot $archiveRoot -FolderName $releaseDir.Name
        Write-Host ('[INFO] Archiving previous release {0} -> {1}' -f $releaseDir.FullName, $archiveDestination)
        Move-Item -LiteralPath $releaseDir.FullName -Destination $archiveDestination
    }
}

function Save-WindowsCredential {
    param(
        [Parameter(Mandatory = $true)]
        [System.Management.Automation.PSCredential]$Credential
    )

    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Credential.Password)
    try {
        $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
        $output = & cmdkey.exe /add:$TargetServer /user:$($Credential.UserName) /pass:$plainPassword 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw ("cmdkey failed: {0}" -f (($output | Out-String).Trim()))
        }
    }
    finally {
        if ($bstr -ne [IntPtr]::Zero) {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
        }
    }
}

function Prompt-And-SaveCredential {
    if (-not [Environment]::UserInteractive) {
        throw "Network share credential is missing and this session is not interactive. Open Windows Credential Manager or rerun interactively."
    }

    Write-Host ('[WARN] Windows Credential Manager credential for \\{0}\{1} was not usable.' -f $TargetServer, $TargetShare)
    Write-Host '[PROMPT] Enter the network-share credential once. It will be saved to Windows Credential Manager and reused on the next build.'

    $credential = Get-Credential -UserName $DefaultUsername -Message ("Credential Manager save for \\{0}\{1}" -f $TargetServer, $TargetShare)
    if (-not $credential) {
        throw "Credential prompt was cancelled."
    }

    Save-WindowsCredential -Credential $credential

    & net.exe use ("\\{0}\{1}" -f $TargetServer, $TargetShare) /delete /y >$null 2>$null
}

try {
    if ($env:PCMT_SKIP_NETWORK_RELEASE -eq "1") {
        Write-Host "[SKIP] Network release publish disabled by PCMT_SKIP_NETWORK_RELEASE=1"
        exit 0
    }

    try {
        Copy-ReleaseBundle -CopyRoot $targetRoot
        Archive-PreviousReleases -CopyRoot $targetRoot -ActiveReleaseName $ReleaseName
        Write-Host ('[OK] Network release published to {0}\{1}' -f $targetRoot, $ReleaseName)
        exit 0
    }
    catch {
        $firstFailure = $_.Exception.Message
        Prompt-And-SaveCredential
        Write-Host ('[INFO] Retrying network copy after saving Windows Credential Manager entry: {0}' -f $firstFailure)
    }

    Copy-ReleaseBundle -CopyRoot $targetRoot
    Archive-PreviousReleases -CopyRoot $targetRoot -ActiveReleaseName $ReleaseName
    Write-Host ('[OK] Network release published to {0}\{1}' -f $targetRoot, $ReleaseName)
    exit 0
}
finally {
    if ($driveName) {
        Remove-PSDrive -Name $driveName -Scope Script -Force -ErrorAction SilentlyContinue
    }
}
