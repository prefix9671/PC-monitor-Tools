# ==========================================
# 사용자 설정 변수 (Configuration)
# ==========================================
param(
    [int]$IntervalSeconds = 30,          # 기록 주기 (초)
    [string[]]$TargetDrives = @("C:", "D:") # 모니터링 드라이브 리스트
)
$LogFolder = "C:\SystemLogs"              # 로그 저장 경로
# ==========================================

if (-not (Test-Path $LogFolder)) { New-Item -ItemType Directory -Path $LogFolder }

Write-Host "Starting Hybrid Resource Monitoring (Interval: $($IntervalSeconds)s)..." -ForegroundColor Cyan
Write-Host "Detecting Hardware (NVIDIA/Intel/AMD)..." -ForegroundColor Yellow

while ($true) {
    # 0. 날짜 기반 로그 분할 및 드라이브 보정
    $CurrentDate = Get-Date -Format "yyyy-MM-dd"
    $LogPath = Join-Path $LogFolder "System_Log_$CurrentDate.csv"
    
    if ($TargetDrives.Count -eq 1) {
        # 문자열 하나로 들어왔을 때 (예: "C:,D:") 분리 처리
        $TargetDrives = $TargetDrives[0] -split ',' | ForEach-Object { $_.Trim().Trim('"').Trim("'") } | Where-Object { $_ -ne "" }
    }

    # 1. 시스템 정보
    $ipObj = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike "*Loopback*" } | Select-Object -First 1
    $ipAddress = if ($ipObj) { $ipObj.IPAddress } else { "N/A" }
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    
    # 물리 장착 메모리 (DIMM 기준)
    $physicalMemGB = [Math]::Round(((Get-CimInstance Win32_PhysicalMemory | Measure-Object Capacity -Sum).Sum / 1GB), 0)
    # OS 사용 가능 메모리
    $osTotalMemGB = [Math]::Round(((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB), 2)

    # 3. 헤더 생성 (프로세스 로그 전용 + 시스템 정적 정보)
    if (-not (Test-Path $LogPath)) {
        # 헤더: 시간, IP, 물리메모리, OS메모리, Top5 메모리, Top5 디스크
        $header = "Timestamp,IP_Address,PhysicalMem(GB),OSTotalMem(GB),Top5_Memory_MB,Top5_Disk_IO_Global(MB/s)"
        Set-Content -Path $LogPath -Value $header -Encoding UTF8
    }

    # 3-1. 시스템 정적 정보 다시 계산 (또는 루프 밖으로 뺄 수 있지만 안전하게 매번 확인)
    # 물리 장착 메모리 (DIMM 기준)
    $physicalMemGB = [Math]::Round(((Get-CimInstance Win32_PhysicalMemory | Measure-Object Capacity -Sum).Sum / 1GB), 0)
    # OS 사용 가능 메모리
    $osTotalMemGB = [Math]::Round(((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB), 2)

    # 4. 상위 프로세스 식별 (메모리)
    $topMemLog = ((Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 5 | ForEach-Object {
                "$($_.ProcessName):$([Math]::Round($_.WorkingSet64 / 1MB, 0))MB"
            }) -join " | ")

    # 5. 상위 프로세스 식별 (디스크 IO)
    $diskCounters = Get-Counter '\Process(*)\IO Data Bytes/sec' -ErrorAction SilentlyContinue
    $diskSamples = $diskCounters.CounterSamples | Where-Object { $_.InstanceName -notmatch "^(_total|idle|system)$" -and $_.CookedValue -gt 10KB }
    $topDiskLog = if ($diskSamples) {
        ($diskSamples | Sort-Object CookedValue -Descending | Select-Object -First 5 | ForEach-Object {
            "$($_.InstanceName):$([Math]::Round($_.CookedValue / 1MB, 2))MB/s"
        }) -join " | "
    }
    else { "No_Active_IO" }

    # 6. 데이터 기록
    $logEntry = "$timestamp,$ipAddress,$physicalMemGB,$osTotalMemGB,""$topMemLog"",""$topDiskLog"""
    Add-Content -Path $LogPath -Value $logEntry
    
    # 실시간 콘솔 출력 (간소화)
    Write-Host "[$timestamp] Process Logged. (Top Mem: $(($topMemLog -split '\|')[0]))" -ForegroundColor Green
    
    Start-Sleep -Seconds $IntervalSeconds
}
